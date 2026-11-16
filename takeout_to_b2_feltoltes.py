"""
Kozvetlen Takeout ZIP -> B2 feltoltes, album-nev alapu celutvonal-szamitassal.

Lasd: mappazasi_algoritmus_specifikacio.md

Hasznalat:
    python takeout_to_b2_feltoltes.py <takeout_zip_utvonal> [--dry-run]

A script NEM ir helyi ideiglenes fajlt (nincs "Veglegesitett kepek" koztes
mappa) - a ZIP-bol kiolvasott bajtok kozvetlenul a B2-re streamelodnek
(rclone rcat). Indulaskor lekeri a mar meglevo B2-tartalom SHA1-listajat,
es kihagyja azokat a fajlokat, amik tartalmilag mar fent vannak (barhol
a volodorben) - igy nem toltodik fel ketszer semmi.

--dry-run: csak kiirja, mit tenne (forras -> cel utvonal, mar fent van /
feltoltesre kerulne), tenylegesen semmit nem tolt fel.
"""

import os
import re
import sys
import csv
import json
import argparse
import zipfile
import hashlib
import unicodedata
import subprocess
from io import BytesIO
from datetime import datetime
from collections import defaultdict
from PIL import Image
from PIL.ExifTags import TAGS
import pillow_heif

pillow_heif.register_heif_opener()

# Csak valódi konzol-stream esetén: a GUI a saját naplóírójával cseréli a stdout-ot,
# pythonw alatt pedig a stdout None is lehet.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Beallitasok
# ---------------------------------------------------------------------------

B2_REMOTE_PREFIX = "b2_storage"
TARGET_BUCKET = "Kepek02"
THUMB_REMOTE = f"{B2_REMOTE_PREFIX}:kepek02-thumbs"
TARGET_REMOTE = f"{B2_REMOTE_PREFIX}:{TARGET_BUCKET}"
# A Lumina Lomtara: a lomtarba helyezett kep fizikailag ide koltozik a Kepek02-bol,
# tombstone csak a Lomtar uritesekor keletkezik. Ezeket sem toltjuk fel ujra.
TRASH_REMOTE = f"{B2_REMOTE_PREFIX}:torles-elott"

# Az éles Lumina Képtár (tablet). Sikeres feltöltés után ennek a Kepek02
# indexét frissítjük (ugyanaz, mint a Connect menü "Resync" gombja).
# Figyelem: a tablet 8080-as portján a HolVan fut, a Lumina a 8000-esen.
LUMINA_URL = "http://192.168.1.157:8000"
# Várakozás a resync előtt: sok B2-művelet után a listázás átmenetileg
# kevesebb fájlt adhat vissza (B2 eshetőleges konzisztencia).
LUMINA_SYNC_DELAY_SEC = 30

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".cr2", ".nef"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".m4v", ".webm"}
THUMB_SIZE = (400, 400)

DAY_ALBUM_RE = re.compile(r"^(\d{4})[_-](\d{2})[_-](\d{2})[ _](.+)$")
MONTH_ALBUM_RE = re.compile(r"^(\d{4})[_-](\d{2})[ _](.+)$")
YEAR_ALBUM_RE = re.compile(r"^(\d{4})[ _](.+)$")
GENERIC_WORDS = ("fotói", "fotoi", "photos", "videói", "videoi")

# Google Photos jelzi a szerkesztett (pl. levágott, retusált) valtozatot egy
# nyelvfuggo utotaggal a fajlnevben - a fioknyelvtol fuggoen "-edited",
# "-szerkesztve" vagy "-szerkesztett" lehet, esetenkent "(1)" tipusu Takeout
# duplikacio-jelzovel a vegen. Ha egy adott mappaban mind az eredeti, mind a
# szerkesztett valtozat megvan, csak a szerkesztettet toltjuk fel - az az
# emberi javitas eredmenye, az eredeti feleslegesse valik.
EDITED_SUFFIX_RE = re.compile(r"^(.*)-(edited|szerkesztve|szerkesztett)(\(\d+\))?$", re.IGNORECASE)

# Fajlnevbol datum kiolvasasahoz - a leggyakoribb kamera/telefon konvenciok
# (pl. "IMG_20211224_181930.jpg", "20210805-125932.jpg"). Csak akkor hasznaljuk
# vegso soron, ha sem EXIF, sem a Takeout JSON-melleklet nem ad datumot - ez
# jobb, mint a ZIP-beli fajl-idobelyeg, ami a Takeout-export csomagolasi
# idejet tukrozi, nem a kep tenyleges keszitesi datumat.
FILENAME_DATETIME_RE = re.compile(r"(\d{4})(\d{2})(\d{2})[_-](\d{2})(\d{2})(\d{2})")
FILENAME_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def strip_edited_suffix(base_name):
    """Ha a fajlnev (kiterjesztes nelkul) szerkesztett-jelzovel vegzodik,
    visszaadja az (alap_nev, True) part, kulonben (base_name, False)."""
    m = EDITED_SUFFIX_RE.match(base_name)
    if m:
        return m.group(1), True
    return base_name, False


# ---------------------------------------------------------------------------
# Kozos segedfuggvenyek (azonosak a sort_by_date.py / prepare_photos.py -val)
# ---------------------------------------------------------------------------

def clean_string(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9.]", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


def match_named_album(folder_name):
    m = DAY_ALBUM_RE.match(folder_name)
    if m:
        return ("day", m.groups())
    m = MONTH_ALBUM_RE.match(folder_name)
    if m:
        return ("month", m.groups())
    m = YEAR_ALBUM_RE.match(folder_name)
    if m:
        year, evname = m.groups()
        low = evname.lower().strip()
        if any(w in low for w in GENERIC_WORDS):
            return None
        return ("year", (year, evname))

    # Datum-elotag nelkuli, tisztan szoveges albumnev (pl. "karacsony").
    # Kizarva: puszta szamjegyekbol allo nev (pl. "2015") es a "@"-ot
    # tartalmazo, megosztott/masik fiokbol importalt album mappaneve.
    stripped = folder_name.strip()
    if stripped and not stripped.isdigit() and "@" not in stripped:
        low = stripped.lower()
        if not any(w in low for w in GENERIC_WORDS):
            return ("text", (stripped,))

    return None


def get_exif_date(image_bytes):
    try:
        img = Image.open(BytesIO(image_bytes))
        exif = img._getexif()
        if exif:
            for tag, value in exif.items():
                if TAGS.get(tag, tag) == "DateTimeOriginal":
                    try:
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
    except Exception:
        pass
    return None


def get_json_metadata_date(zf, internal_path):
    """A Google Takeout az eredeti felvetel idejet egy melle-fajl JSON-ban
    tarolja (pl. 'kep.jpg.json' vagy ujabban 'kep.jpg.supplemental-metadata.json'),
    a "photoTakenTime" unix idobelyegkent. Ez akkor is megbizhato, ha a kep
    sajat EXIF-je hianyzik vagy serult (pl. Google Photos altal szerkesztett
    valtozatoknal gyakori)."""
    for suffix in (".supplemental-metadata.json", ".json"):
        candidate = internal_path + suffix
        try:
            raw = zf.read(candidate)
        except KeyError:
            continue
        try:
            meta = json.loads(raw)
            ts = meta.get("photoTakenTime", {}).get("timestamp")
            if ts:
                return datetime.fromtimestamp(int(ts))
        except Exception:
            continue
    return None


def parse_date_from_filename(filename):
    """Utolso esely a datum kitalalasara, mielott a ZIP-beli (a Takeout-export
    csomagolasi idejet tukrozo, megbizhatatlan) fajl-idobelyeghez nyulnank -
    a leggyakoribb kamera/telefon fajlnev-konvenciokat probalja (pl.
    "IMG_20211224_181930.jpg", "20210805-125932.jpg")."""
    base = os.path.splitext(os.path.basename(filename))[0]
    current_year = datetime.now().year

    m = FILENAME_DATETIME_RE.search(base)
    if m:
        try:
            y, mo, d, h, mi, s = (int(g) for g in m.groups())
            if 1995 <= y <= current_year + 1:
                return datetime(y, mo, d, h, mi, s)
        except ValueError:
            pass

    m = FILENAME_DATE_RE.search(base)
    if m:
        try:
            y, mo, d = (int(g) for g in m.groups())
            if 1995 <= y <= current_year + 1:
                return datetime(y, mo, d)
        except ValueError:
            pass

    return None


def sha1_of_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def compute_b2_key(dt, album_match, filename):
    """Mindig '/'-lel elvalasztott B2-kulcsot ad vissza (nem os.path.join!)."""
    name, ext = os.path.splitext(filename)
    clean_name = clean_string(name)
    ext = ext.lower()
    if ext in (".heic", ".heif"):
        ext = ".jpg"

    if album_match:
        kind, groups = album_match
        if kind == "day":
            evname = groups[3]
        elif kind == "month":
            evname = groups[2]
        elif kind == "text":
            evname = groups[0]
        else:
            evname = groups[1]
        evname_clean = clean_string(evname)
        sub = f"{dt.day:02d}-{evname_clean}" if evname_clean else f"{dt.day:02d}"
        return f"{dt.year:04d}/{dt.month:02d}/{sub}/{clean_name}{ext}"

    return f"{dt.year:04d}/{dt.month:02d}/{clean_name}{ext}"


def to_jpeg_bytes(pil_img, quality=95):
    out = BytesIO()
    if pil_img.mode in ("RGBA", "P"):
        pil_img = pil_img.convert("RGB")
    pil_img.save(out, "JPEG", quality=quality)
    return out.getvalue()


def create_thumbnail_bytes(image_bytes):
    img = Image.open(BytesIO(image_bytes))
    if hasattr(img, "_getexif"):
        exif = img._getexif()
        if exif:
            orientation = exif.get(0x0112)
            if orientation == 3:
                img = img.rotate(180, expand=True)
            elif orientation == 6:
                img = img.rotate(270, expand=True)
            elif orientation == 8:
                img = img.rotate(90, expand=True)
    img.thumbnail(THUMB_SIZE, Image.Resampling.LANCZOS)
    out = BytesIO()
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.save(out, "JPEG", quality=75, optimize=True)
    return out.getvalue()


# ---------------------------------------------------------------------------
# B2 / rclone
# ---------------------------------------------------------------------------

def load_existing_b2_sha1(remote):
    print(f"Meglévő B2-tartalom SHA1-listájának lekérése ({remote})...", flush=True)
    cmd = ["rclone", "lsjson", "--hash", "--recursive", remote]
    result = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode != 0:
        print("HIBA az rclone lsjson futtatása során:", flush=True)
        print(result.stderr, flush=True)
        # Üres listával folytatni duplikált feltöltést okozna, ezért megállunk.
        raise RuntimeError("A B2-tartalom SHA1-listája nem kérhető le, a feltöltés leállt.")
    data = json.loads(result.stdout)
    hashes = {(f.get("Hashes") or {}).get("sha1") for f in data}
    hashes.discard(None)
    print(f"  {len(hashes)} meglévő SHA1 betöltve.", flush=True)
    return hashes


def rclone_upload_bytes(data: bytes, remote_path: str):
    cmd = ["rclone", "rcat", remote_path]
    result = subprocess.run(cmd, input=data, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode != 0:
        print(f"  [Feltöltési hiba] {remote_path}: "
              f"{result.stderr.decode('utf-8', errors='replace')}", flush=True)
        return False
    return True


# ---------------------------------------------------------------------------
# Szandekosan torolt kepek (Lumina tombstone lista)
# ---------------------------------------------------------------------------

DELETED_SHA1_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deleted_sha1_list.csv"
)


def load_deleted_sha1_set():
    """Beolvassa a Lumina Kepnezegeto altal irt deleted_sha1_list.csv-t (ha van),
    hogy ne toltsunk fel ujra olyan kepet, amit mar szandekosan, veglegesen
    torolt a felhasznalo a Lomtarbol."""
    if not os.path.exists(DELETED_SHA1_CSV):
        print(f"Nincs torolt-tartalom lista ezen az uton (ez rendben van, ha meg "
              f"soha nem urult ki a Lomtar): {DELETED_SHA1_CSV}", flush=True)
        return set()

    hashes = set()
    with open(DELETED_SHA1_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            h = row.get("sha1")
            if h:
                hashes.add(h)
    print(f"Szandekosan torolt tartalom listaja betoltve: {len(hashes)} SHA1.", flush=True)
    return hashes


# ---------------------------------------------------------------------------
# Egy fajl feltoltese + naplo (kozos a normal futas es az ujraprobalas kozott)
# ---------------------------------------------------------------------------

FAILED_STATUS = "feltoltesi-hiba"
PLAN_FIELDS = ["takeout_utvonal", "sha1", "statusz", "cel_utvonal"]


def upload_one(data: bytes, filename: str, b2_key: str) -> bool:
    """Feltölt egy képet (HEIC -> JPG konverzióval, ha kell) és a bélyegképét.
    True, ha mindkettő sikerült."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".heic", ".heif"):
        upload_bytes = to_jpeg_bytes(Image.open(BytesIO(data)))
    else:
        upload_bytes = data

    thumb_bytes = create_thumbnail_bytes(data)

    ok_main = rclone_upload_bytes(upload_bytes, f"{TARGET_REMOTE}/{b2_key}")
    # Bélyegképet csak sikeres eredeti-feltöltés után töltünk fel, hogy ne
    # maradjon árva bélyegkép eredeti nélkül.
    return ok_main and rclone_upload_bytes(thumb_bytes, f"{THUMB_REMOTE}/{b2_key}")


def plan_csv_path_for(zip_path):
    zip_basename = os.path.splitext(os.path.basename(zip_path))[0]
    out_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(out_dir, f"feltoltes_terv_{zip_basename}.csv")


def write_plan_csv(plan_csv, rows):
    """Kiírja a naplót. A mappa egy élő Google Drive szinkron alá tartozik, ami
    új fájlok létrehozásakor néha rövid ideig zárolja azokat - ezért néhány
    újrapróbálkozással írjuk ki, hogy egy átmeneti zárolás ne szakítsa meg a
    már elvégzett munkát. Visszaadja az útvonalat, vagy None-t, ha nem sikerült."""
    import time
    for attempt in range(1, 6):
        try:
            with open(plan_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=PLAN_FIELDS)
                writer.writeheader()
                writer.writerows(rows)
            return plan_csv
        except PermissionError as e:
            if attempt == 5:
                print(f"\nFIGYELMEZTETES: a naplo CSV irasa {attempt} probalkozas utan is "
                      f"sikertelen (feltehetoen atmeneti Google Drive zarolas): {e}", flush=True)
                return None
            print(f"  [Ujraprobalkozas {attempt}/5] Naplo CSV zarolva, varok 1 mp-et...", flush=True)
            time.sleep(1)


def trigger_lumina_resync(lumina_url=LUMINA_URL, delay_sec=LUMINA_SYNC_DELAY_SEC):
    """Elindítja a Lumina Képtárban a Kepek02 fiók újraindexelését (ugyanazt,
    amit a Connect menü "Resync" gombja). Hiba esetén csak figyelmeztet -
    a feltöltés eredményét ez nem befolyásolja. True, ha elindult."""
    import time
    import urllib.request
    print(f"\n--- Lumina Képtár index frissítése ({lumina_url}) ---", flush=True)
    if delay_sec:
        print(f"Várok {delay_sec} mp-et, hogy a B2 listázás biztosan mutassa az új fájlokat...", flush=True)
        time.sleep(delay_sec)
    try:
        with urllib.request.urlopen(f"{lumina_url}/b2/accounts", timeout=15) as resp:
            accounts = json.load(resp)
        account = next((a for a in accounts
                        if (a.get("bucket_name") or "").lower() == TARGET_BUCKET.lower()), None)
        if account is None:
            print(f"FIGYELMEZTETÉS: a Luminában nincs '{TARGET_BUCKET}' vödrű fiók, "
                  f"a frissítés kimaradt.", flush=True)
            return False
        req = urllib.request.Request(f"{lumina_url}/b2/sync/{account['id']}", method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        print(f"A Kepek02 index frissítése elindult a Luminában (fiók #{account['id']}). "
              f"Az állapota a Connect menüben követhető.", flush=True)
        return True
    except Exception as e:
        print(f"FIGYELMEZTETÉS: a Lumina nem érhető el, az index frissítése kimaradt ({e}). "
              f"Később a Connect menü Resync gombjával indítható.", flush=True)
        return False


# ---------------------------------------------------------------------------
# Fo folyamat
# ---------------------------------------------------------------------------

def process_zip(zip_path, dry_run=True, lumina_sync=False):
    print(f"--- Takeout ZIP feldolgozása: {zip_path} ---", flush=True)
    print(f"Mód: {'DRY-RUN (nem tölt fel semmit)' if dry_run else 'ÉLES FELTÖLTÉS'}", flush=True)

    if not os.path.exists(zip_path):
        print(f"HIBA: nem létezik a fájl: {zip_path}")
        return

    existing_sha1 = load_existing_b2_sha1(TARGET_REMOTE)
    trash_sha1 = load_existing_b2_sha1(TRASH_REMOTE)
    deleted_sha1 = load_deleted_sha1_set()

    # --- 1. lepes: ZIP tartalmanak indexelese SHA1 szerint ---
    print("\n--- 1. lépés: ZIP tartalmának indexelése (SHA1) ---", flush=True)
    by_hash = defaultdict(list)  # sha1 -> [(internal_path, album_folder, filename), ...]
    total_entries = 0
    video_skipped = 0

    edited_originals_skipped = 0

    with zipfile.ZipFile(zip_path) as zf:
        infolist = [i for i in zf.infolist() if not i.is_dir()]

        # Elozetes fajlnev-alapu vizsgalat (tartalom-olvasas nelkul): mely
        # (mappa, alapnev, kiterjesztes) parokhoz letezik szerkesztett valtozat
        # ugyanabban a mappaban.
        edited_present = set()
        for info in infolist:
            ext = os.path.splitext(info.filename)[1].lower()
            if ext not in IMAGE_EXTENSIONS:
                continue
            directory = os.path.dirname(info.filename.replace("\\", "/"))
            base_name = os.path.splitext(os.path.basename(info.filename))[0]
            core_base, is_edited = strip_edited_suffix(base_name)
            if is_edited:
                edited_present.add((directory, core_base.lower(), ext))

        for idx, info in enumerate(infolist, 1):
            ext = os.path.splitext(info.filename)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                video_skipped += 1
                continue
            if ext not in IMAGE_EXTENSIONS:
                continue

            directory = os.path.dirname(info.filename.replace("\\", "/"))
            base_name = os.path.splitext(os.path.basename(info.filename))[0]
            core_base, is_edited = strip_edited_suffix(base_name)
            if not is_edited and (directory, core_base.lower(), ext) in edited_present:
                # Van szerkesztett valtozat ugyanebben a mappaban - az eredetit
                # kihagyjuk, csak a javitott (szerkesztett) valtozat megy be a B2-be.
                edited_originals_skipped += 1
                print(f"  [KIHAGYVA - van szerkesztett változat] {info.filename}", flush=True)
                continue

            try:
                data = zf.read(info)
            except Exception as e:
                print(f"  [Olvasási hiba] {info.filename}: {e}", flush=True)
                continue

            sha1 = sha1_of_bytes(data)
            parts = info.filename.replace("\\", "/").split("/")
            album_folder = parts[-2] if len(parts) >= 2 else ""
            filename = os.path.basename(info.filename)
            by_hash[sha1].append((info.filename, album_folder, filename))
            total_entries += 1

            if idx % 100 == 0:
                print(f"  ... {idx}/{len(infolist)} bejegyzés átnézve", flush=True)

        print(f"Indexelés kész: {total_entries} kép, {video_skipped} videó kihagyva "
              f"(nem támogatott), {edited_originals_skipped} eredeti kihagyva (van szerkesztett "
              f"változat), {len(by_hash)} egyedi tartalom.", flush=True)

        # Elozetes szamolas, hogy a feltoltesi ciklus alatt egy stabil "X/Y"
        # szamlalot tudjunk mutatni - a tenylegesen feltoltendo (meg nem
        # letezo, nem szandekosan torolt) tartalmak darabszama.
        total_to_upload = sum(
            1 for sha1 in by_hash
            if sha1 not in existing_sha1 and sha1 not in trash_sha1 and sha1 not in deleted_sha1
        )
        print(f"Ténylegesen feltöltendő (még nincs fent): {total_to_upload} db", flush=True)

        # --- 2. lepes: dontes + feltoltes ---
        print("\n--- 2. lépés: célútvonal-számítás és feltöltés ---", flush=True)
        plan_rows = []
        to_upload = 0
        already_exists = 0
        uploaded_ok = 0
        upload_failed = 0
        deliberately_skipped = 0
        in_trash_skipped = 0

        for sha1, occurrences in by_hash.items():
            chosen_internal = None
            chosen_filename = None
            chosen_album_match = None
            for internal_path, album_folder, filename in occurrences:
                m = match_named_album(album_folder)
                if m:
                    chosen_internal, chosen_filename, chosen_album_match = internal_path, filename, m
                    break
            if chosen_internal is None:
                chosen_internal, _, chosen_filename = occurrences[0]
                chosen_album_match = None

            if sha1 in existing_sha1:
                already_exists += 1
                plan_rows.append({
                    "takeout_utvonal": chosen_internal, "sha1": sha1,
                    "statusz": "mar-fent-van", "cel_utvonal": "",
                })
                continue

            if sha1 in trash_sha1:
                in_trash_skipped += 1
                plan_rows.append({
                    "takeout_utvonal": chosen_internal, "sha1": sha1,
                    "statusz": "lomtarban-van", "cel_utvonal": "",
                })
                print(f"  [KIHAGYVA - a Lomtárban van] {chosen_internal}", flush=True)
                continue

            if sha1 in deleted_sha1:
                deliberately_skipped += 1
                plan_rows.append({
                    "takeout_utvonal": chosen_internal, "sha1": sha1,
                    "statusz": "szandekosan-torolve-nem-toltjuk-fel", "cel_utvonal": "",
                })
                print(f"  [KIHAGYVA - korabban torolve] {chosen_internal}", flush=True)
                continue

            # Csak most olvassuk vissza a bajtokat (a valasztott peldanyt)
            info = zf.getinfo(chosen_internal)
            data = zf.read(info)
            # Prioritas: EXIF -> Takeout JSON-melleklet (photoTakenTime) ->
            # fajlnevbol kiolvasott datum -> vegso esetben a ZIP-beli fajl-
            # idobelyeg (ami a Takeout-export csomagolasi idejet tukrozi,
            # NEM a kep tenyleges keszitesi datumat - lasd a fenti fuggvenyek
            # dokumentaciojat).
            effective_date = (
                get_exif_date(data)
                or get_json_metadata_date(zf, chosen_internal)
                or parse_date_from_filename(chosen_filename)
                or datetime(*info.date_time)
            )

            b2_key = compute_b2_key(effective_date, chosen_album_match, chosen_filename)
            to_upload += 1

            if dry_run:
                plan_rows.append({
                    "takeout_utvonal": chosen_internal, "sha1": sha1,
                    "statusz": "feltoltesre-kerulne", "cel_utvonal": b2_key,
                })
                print(f"  [{to_upload}/{total_to_upload}] [DRY-RUN] {chosen_internal}  ->  {TARGET_BUCKET}/{b2_key}", flush=True)
                continue

            if upload_one(data, chosen_filename, b2_key):
                uploaded_ok += 1
                print(f"  [{to_upload}/{total_to_upload}] [OK] {chosen_internal}  ->  {TARGET_BUCKET}/{b2_key}", flush=True)
                plan_rows.append({
                    "takeout_utvonal": chosen_internal, "sha1": sha1,
                    "statusz": "feltoltve", "cel_utvonal": b2_key,
                })
            else:
                upload_failed += 1
                print(f"  [{to_upload}/{total_to_upload}] [HIBA] {chosen_internal}  ->  {TARGET_BUCKET}/{b2_key}", flush=True)
                plan_rows.append({
                    "takeout_utvonal": chosen_internal, "sha1": sha1,
                    "statusz": FAILED_STATUS, "cel_utvonal": b2_key,
                })

    # --- Osszefoglalo + naplo CSV ---
    # A mappa egy elo Google Drive szinkron ala tartozik, ami uj fajlok
    # letrehozasakor néha rovid ideig zarolja azokat (ugyanaz a jelenseg,
    # mint a git packed-refs.lock hibaja ebben a repoban) - ezert nehany
    # ujraprobalkozassal irjuk ki, hogy egy atmeneti zarolas ne szakitsa
    # meg a mar elvegzett munkat (feltoltes/dry-run terv) csak a naplo miatt.
    plan_csv = write_plan_csv(plan_csv_path_for(zip_path), plan_rows)

    print("\n--- KÉSZ ---", flush=True)
    print(f"Egyedi tartalom összesen: {len(by_hash)}", flush=True)
    print(f"Eredeti kihagyva (van szerkesztett változat): {edited_originals_skipped}", flush=True)
    print(f"Már fent volt (kihagyva): {already_exists}", flush=True)
    print(f"A Lomtárban van (kihagyva): {in_trash_skipped}", flush=True)
    print(f"Szándékosan korábban törölve (kihagyva): {deliberately_skipped}", flush=True)
    print(f"Feltöltésre szánt: {to_upload}", flush=True)
    if not dry_run:
        print(f"Sikeresen feltöltve: {uploaded_ok}", flush=True)
        print(f"Feltöltési hiba: {upload_failed}", flush=True)
        if upload_failed:
            print("FIGYELEM: néhány kép feltöltése nem sikerült ('feltoltesi-hiba' a naplóban). "
                  "A 'Hibás fájlok újrapróbálása' gombbal (vagy --retry-failed kapcsolóval) "
                  "csak ezeket lehet újra megpróbálni.", flush=True)
    print(f"Napló mentve: {plan_csv}" if plan_csv else "Napló NEM mentődött (lásd fenti figyelmeztetés).", flush=True)
    if lumina_sync and not dry_run and uploaded_ok:
        trigger_lumina_resync()
    return plan_csv


def count_failed_in_plan(plan_csv):
    """A naplóban lévő 'feltoltesi-hiba' státuszú sorok száma (0, ha nincs napló)."""
    if not plan_csv or not os.path.exists(plan_csv):
        return 0
    with open(plan_csv, newline="", encoding="utf-8") as f:
        return sum(1 for row in csv.DictReader(f) if row.get("statusz") == FAILED_STATUS)


def retry_failed(zip_path, plan_csv=None, lumina_sync=False):
    """Csak a napló 'feltoltesi-hiba' sorait próbálja újra feltölteni, ugyanarra
    a célútvonalra, mint az első körben. Nem kéri le újra a B2 SHA1-listáját és
    nem indexeli újra a ZIP-et. A naplót helyben frissíti (sikeres sor ->
    'feltoltve'), így többször is futtatható, amíg el nem fogynak a hibák."""
    plan_csv = plan_csv or plan_csv_path_for(zip_path)
    print(f"--- Hibás fájlok újrapróbálása: {zip_path} ---", flush=True)
    if not os.path.exists(zip_path):
        print(f"HIBA: nem létezik a fájl: {zip_path}", flush=True)
        return None
    if not os.path.exists(plan_csv):
        print(f"HIBA: nincs napló ehhez a ZIP-hez: {plan_csv}", flush=True)
        return None

    with open(plan_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    failed_rows = [r for r in rows if r.get("statusz") == FAILED_STATUS]
    total = len(failed_rows)
    print(f"Újrapróbálandó: {total} db", flush=True)
    if not total:
        return plan_csv

    ok_count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for idx, row in enumerate(failed_rows, 1):
            internal = row["takeout_utvonal"]
            b2_key = row["cel_utvonal"]
            try:
                data = zf.read(internal)
            except Exception as e:
                print(f"  [{idx}/{total}] [Olvasási hiba] {internal}: {e}", flush=True)
                continue
            if upload_one(data, os.path.basename(internal), b2_key):
                row["statusz"] = "feltoltve"
                ok_count += 1
                print(f"  [{idx}/{total}] [OK] {internal}  ->  {TARGET_BUCKET}/{b2_key}", flush=True)
            else:
                print(f"  [{idx}/{total}] [HIBA] {internal}  ->  {TARGET_BUCKET}/{b2_key}", flush=True)

    saved = write_plan_csv(plan_csv, rows)
    print("\n--- ÚJRAPRÓBÁLÁS KÉSZ ---", flush=True)
    print(f"Sikeresen feltöltve: {ok_count}", flush=True)
    print(f"Továbbra is hibás: {total - ok_count}", flush=True)
    print(f"Napló frissítve: {saved}" if saved else "Napló NEM mentődött (lásd fenti figyelmeztetés).", flush=True)
    if lumina_sync and ok_count:
        trigger_lumina_resync()
    return saved


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Közvetlen Takeout ZIP -> B2 feltöltés, album-név alapú célútvonal-számítással."
    )
    parser.add_argument("zip_path", help="A Takeout ZIP fájl útvonala.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Csak kiírja, mit tenne, ténylegesen nem tölt fel semmit."
    )
    parser.add_argument(
        "--retry-failed", action="store_true",
        help="Csak a korábbi futás naplójában 'feltoltesi-hiba' státuszú fájlokat próbálja újra."
    )
    parser.add_argument(
        "--no-lumina-sync", action="store_true",
        help="Sikeres feltöltés után NE indítsa el a Lumina Kepek02 index frissítését."
    )
    args = parser.parse_args()
    zip_arg = args.zip_path.strip().strip('"')
    sync = not args.no_lumina_sync
    if args.retry_failed:
        retry_failed(zip_arg, lumina_sync=sync)
    else:
        process_zip(zip_arg, dry_run=args.dry_run, lumina_sync=sync)
