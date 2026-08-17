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

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Beallitasok
# ---------------------------------------------------------------------------

B2_REMOTE_PREFIX = "b2_storage"
TARGET_BUCKET = "Kepek02"
THUMB_REMOTE = f"{B2_REMOTE_PREFIX}:kepek02-thumbs"
TARGET_REMOTE = f"{B2_REMOTE_PREFIX}:{TARGET_BUCKET}"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".cr2", ".nef"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".m4v", ".webm"}
THUMB_SIZE = (400, 400)

DAY_ALBUM_RE = re.compile(r"^(\d{4})[_-](\d{2})[_-](\d{2})[ _](.+)$")
MONTH_ALBUM_RE = re.compile(r"^(\d{4})[_-](\d{2})[ _](.+)$")
YEAR_ALBUM_RE = re.compile(r"^(\d{4})[ _](.+)$")
GENERIC_WORDS = ("fotói", "fotoi", "photos", "videói", "videoi")


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
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("HIBA az rclone lsjson futtatása során:", flush=True)
        print(result.stderr, flush=True)
        return set()
    data = json.loads(result.stdout)
    hashes = {(f.get("Hashes") or {}).get("sha1") for f in data}
    hashes.discard(None)
    print(f"  {len(hashes)} meglévő SHA1 betöltve.", flush=True)
    return hashes


def rclone_upload_bytes(data: bytes, remote_path: str):
    cmd = ["rclone", "rcat", remote_path]
    result = subprocess.run(cmd, input=data, capture_output=True)
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
# Fo folyamat
# ---------------------------------------------------------------------------

def process_zip(zip_path, dry_run=True):
    print(f"--- Takeout ZIP feldolgozása: {zip_path} ---", flush=True)
    print(f"Mód: {'DRY-RUN (nem tölt fel semmit)' if dry_run else 'ÉLES FELTÖLTÉS'}", flush=True)

    if not os.path.exists(zip_path):
        print(f"HIBA: nem létezik a fájl: {zip_path}")
        return

    existing_sha1 = load_existing_b2_sha1(TARGET_REMOTE)
    deleted_sha1 = load_deleted_sha1_set()

    # --- 1. lepes: ZIP tartalmanak indexelese SHA1 szerint ---
    print("\n--- 1. lépés: ZIP tartalmának indexelése (SHA1) ---", flush=True)
    by_hash = defaultdict(list)  # sha1 -> [(internal_path, album_folder, filename), ...]
    total_entries = 0
    video_skipped = 0

    with zipfile.ZipFile(zip_path) as zf:
        infolist = [i for i in zf.infolist() if not i.is_dir()]
        for idx, info in enumerate(infolist, 1):
            ext = os.path.splitext(info.filename)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                video_skipped += 1
                continue
            if ext not in IMAGE_EXTENSIONS:
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
              f"(nem támogatott), {len(by_hash)} egyedi tartalom.", flush=True)

        # --- 2. lepes: dontes + feltoltes ---
        print("\n--- 2. lépés: célútvonal-számítás és feltöltés ---", flush=True)
        plan_rows = []
        to_upload = 0
        already_exists = 0
        uploaded_ok = 0
        upload_failed = 0
        deliberately_skipped = 0

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
            exif_date = get_exif_date(data)
            effective_date = exif_date or datetime(*info.date_time)

            b2_key = compute_b2_key(effective_date, chosen_album_match, chosen_filename)
            to_upload += 1

            if dry_run:
                plan_rows.append({
                    "takeout_utvonal": chosen_internal, "sha1": sha1,
                    "statusz": "feltoltesre-kerulne", "cel_utvonal": b2_key,
                })
                print(f"  [DRY-RUN] {chosen_internal}  ->  {TARGET_BUCKET}/{b2_key}", flush=True)
                continue

            # HEIC -> JPG konverzio, ha kell
            ext = os.path.splitext(chosen_filename)[1].lower()
            if ext in (".heic", ".heif"):
                img = Image.open(BytesIO(data))
                upload_bytes = to_jpeg_bytes(img)
            else:
                upload_bytes = data

            thumb_bytes = create_thumbnail_bytes(data)

            ok_main = rclone_upload_bytes(upload_bytes, f"{TARGET_REMOTE}/{b2_key}")
            ok_thumb = rclone_upload_bytes(thumb_bytes, f"{THUMB_REMOTE}/{b2_key}")

            if ok_main and ok_thumb:
                uploaded_ok += 1
                print(f"  [OK] {chosen_internal}  ->  {TARGET_BUCKET}/{b2_key}", flush=True)
                plan_rows.append({
                    "takeout_utvonal": chosen_internal, "sha1": sha1,
                    "statusz": "feltoltve", "cel_utvonal": b2_key,
                })
            else:
                upload_failed += 1
                plan_rows.append({
                    "takeout_utvonal": chosen_internal, "sha1": sha1,
                    "statusz": "feltoltesi-hiba", "cel_utvonal": b2_key,
                })

    # --- Osszefoglalo + naplo CSV ---
    zip_basename = os.path.splitext(os.path.basename(zip_path))[0]
    out_dir = os.path.dirname(os.path.abspath(__file__))
    plan_csv = os.path.join(out_dir, f"feltoltes_terv_{zip_basename}.csv")
    with open(plan_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["takeout_utvonal", "sha1", "statusz", "cel_utvonal"])
        writer.writeheader()
        writer.writerows(plan_rows)

    print("\n--- KÉSZ ---", flush=True)
    print(f"Egyedi tartalom összesen: {len(by_hash)}", flush=True)
    print(f"Már fent volt (kihagyva): {already_exists}", flush=True)
    print(f"Szándékosan korábban törölve (kihagyva): {deliberately_skipped}", flush=True)
    print(f"Feltöltésre szánt: {to_upload}", flush=True)
    if not dry_run:
        print(f"Sikeresen feltöltve: {uploaded_ok}", flush=True)
        print(f"Feltöltési hiba: {upload_failed}", flush=True)
    print(f"Napló mentve: {plan_csv}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Közvetlen Takeout ZIP -> B2 feltöltés, album-név alapú célútvonal-számítással."
    )
    parser.add_argument("zip_path", help="A Takeout ZIP fájl útvonala.")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Csak kiírja, mit tenne, ténylegesen nem tölt fel semmit."
    )
    args = parser.parse_args()
    process_zip(args.zip_path.strip().strip('"'), dry_run=args.dry_run)
