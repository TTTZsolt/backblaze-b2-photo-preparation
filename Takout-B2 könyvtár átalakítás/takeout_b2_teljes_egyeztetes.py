"""
Takeout <-> B2 teljes konyvtar-strukturaegyeztetes.

Ezt a szkriptet a LENOVO-n kell futtatni (ott vannak a Takeout ZIP-ek).

Mit csinal:
  1. Bejarja a teljes Takeout mappat (ZIP-eken belul es azon kivul is),
     minden kep- es videofajlhoz kiszamolja a SHA1-et es (kepeknel) kiolvassa
     az EXIF DateTimeOriginal-t (ha nincs, a fajl/zip-bejegyzes modositasi idejet).
  2. Lekeri a B2 "Kepek02" vodor teljes tartalmat rclone-nal (mar telepitve/
     konfiguralva van ezen a gepen, l. prepare_photos.py) - a B2 natívan
     tarolja a SHA1-et minden fajlhoz, tehat ehhez nem kell letoltes.
  3. A ket listat SHA1 alapjan osszefuzi, es minden Takeout-fajlhoz
     kiszamolja a sort_by_date.py + prepare_photos.py logikaja alapjan VART
     B2 utvonalat, majd osszeveti a TENYLEGES B2 utvonallal (ha van).
  4. Kiir egy reszletes CSV-t es egy osszefoglalo MD-t.

Futtatas:
    python takeout_b2_teljes_egyeztetes.py

Fuggosegek: Pillow (mar telepitve van a projekt kornyezeteben).
"""

import os
import re
import sys
import csv
import json
import zipfile
import hashlib
import unicodedata
import subprocess
from io import BytesIO
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS

# A Windows konzol/naplofajl alapertelmezett kodolasa (cp1252) nem tudja
# kiirni az ekezetes (pl. magyar utvonalakban levo) karaktereket - ez a
# program leallasat okozta. Kikenyszeritjuk az UTF-8 kimenetet, es ha
# egy karakter meg ugy sem irhato ki, helyettesitovel cserejuk, ne alljon le.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Beallitasok
# ---------------------------------------------------------------------------

TAKEOUT_ROOT = r"C:\Users\zsolt.tuske\Pictures\Takeout"
B2_REMOTE = "b2_storage:Kepek02"

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
TAKEOUT_INDEX_CSV = os.path.join(OUTPUT_DIR, "takeout_teljes_index.csv")
B2_LISTING_JSON = os.path.join(OUTPUT_DIR, "b2_kepek02_listing.json")
FINAL_CSV = os.path.join(OUTPUT_DIR, "takeout_b2_teljes_egyeztetes.csv")
SUMMARY_MD = os.path.join(OUTPUT_DIR, "takeout_b2_teljes_egyeztetes.md")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".cr2", ".nef", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".m4v", ".webm"}


# ---------------------------------------------------------------------------
# Segedfuggvenyek - a prepare_photos.py-bol atvett tisztitasi logika
# ---------------------------------------------------------------------------

def clean_string(text):
    """Ugyanaz a logika, mint a prepare_photos.py clean_string() fuggvenyeben."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9.]", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


def sha1_of_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def get_exif_date(image_bytes: bytes):
    """DateTimeOriginal kiolvasasa, ugyanugy mint a sort_by_date.py-ban."""
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


def predict_b2_path(effective_date: datetime, filename: str):
    """A sort_by_date.py + prepare_photos.py egyuttes logikaja alapjan
    kiszamitott VART B2 utvonal."""
    if not effective_date:
        return None
    year = effective_date.strftime("%Y")
    month = effective_date.strftime("%m")
    name, ext = os.path.splitext(filename)
    clean_name = clean_string(name)
    ext = ext.lower()
    if ext in (".heic", ".heif"):
        ext = ".jpg"
    return f"{year}/{month}/{clean_name}{ext}"


# ---------------------------------------------------------------------------
# 1. lepes: Takeout teljes indexelese
# ---------------------------------------------------------------------------

def index_takeout():
    rows = []
    print(f"--- Takeout bejarasa: {TAKEOUT_ROOT} ---")

    if not os.path.exists(TAKEOUT_ROOT):
        print(f"HIBA: nem letezik a mappa: {TAKEOUT_ROOT}")
        return rows

    for root, dirs, files in os.walk(TAKEOUT_ROOT):
        for fn in files:
            full_path = os.path.join(root, fn)
            ext = os.path.splitext(fn)[1].lower()

            if ext == ".zip":
                try:
                    with zipfile.ZipFile(full_path) as zf:
                        entries = [i for i in zf.infolist() if not i.is_dir()]
                        print(f"ZIP feldolgozasa: {os.path.basename(full_path)} "
                              f"({len(entries)} bejegyzes) - eddig osszesen {len(rows)} feldolgozva",
                              flush=True)
                        zip_processed = 0
                        for info in entries:
                            inner_ext = os.path.splitext(info.filename)[1].lower()
                            is_video = inner_ext in VIDEO_EXTENSIONS
                            is_image = inner_ext in IMAGE_EXTENSIONS
                            if not is_video and not is_image:
                                continue
                            try:
                                data = zf.read(info)
                            except Exception as e:
                                print(f"  [ZIP olvasasi hiba] {info.filename}: {e}", flush=True)
                                continue

                            sha1 = sha1_of_bytes(data)
                            exif_date = get_exif_date(data) if is_image else None
                            fallback_date = datetime(*info.date_time)
                            effective_date = exif_date or fallback_date

                            rows.append({
                                "source_zip": os.path.basename(full_path),
                                "internal_path": info.filename,
                                "filename": os.path.basename(info.filename),
                                "size": info.file_size,
                                "sha1": sha1,
                                "exif_date": exif_date.strftime("%Y-%m-%d %H:%M:%S") if exif_date else "",
                                "fallback_mtime": fallback_date.strftime("%Y-%m-%d %H:%M:%S"),
                                "effective_date": effective_date.strftime("%Y-%m-%d %H:%M:%S"),
                                "is_video": is_video,
                            })

                            zip_processed += 1
                            if zip_processed % 100 == 0:
                                print(f"  ... {zip_processed}/{len(entries)} kesz ebben a ZIP-ben "
                                      f"(osszesen: {len(rows)})", flush=True)
                except zipfile.BadZipFile:
                    print(f"  [Hibas ZIP] {full_path}", flush=True)

            elif ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                is_video = ext in VIDEO_EXTENSIONS
                is_image = ext in IMAGE_EXTENSIONS
                try:
                    with open(full_path, "rb") as f:
                        data = f.read()
                    sha1 = sha1_of_bytes(data)
                    exif_date = get_exif_date(data) if is_image else None
                    fallback_date = datetime.fromtimestamp(os.path.getmtime(full_path))
                    effective_date = exif_date or fallback_date
                    rel = os.path.relpath(full_path, TAKEOUT_ROOT)

                    rows.append({
                        "source_zip": "",
                        "internal_path": rel,
                        "filename": fn,
                        "size": len(data),
                        "sha1": sha1,
                        "exif_date": exif_date.strftime("%Y-%m-%d %H:%M:%S") if exif_date else "",
                        "fallback_mtime": fallback_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "effective_date": effective_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "is_video": is_video,
                    })
                except Exception as e:
                    print(f"  [Fajl olvasasi hiba] {full_path}: {e}", flush=True)

                if len(rows) % 100 == 0:
                    print(f"  ... eddig osszesen {len(rows)} bejegyzes feldolgozva", flush=True)

    print(f"Takeout index kesz: {len(rows)} bejegyzes.", flush=True)

    with open(TAKEOUT_INDEX_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["source_zip", "internal_path", "filename", "size", "sha1",
                      "exif_date", "fallback_mtime", "effective_date", "is_video"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Mentve: {TAKEOUT_INDEX_CSV}", flush=True)

    return rows


# ---------------------------------------------------------------------------
# 2. lepes: B2 Kepek02 vodor listazasa rclone-nal (SHA1-gyel egyutt)
# ---------------------------------------------------------------------------

def list_b2():
    print(f"\n--- B2 '{B2_REMOTE}' vodor listazasa rclone-nal (ez eltarthat egy percig) ---", flush=True)
    cmd = ["rclone", "lsjson", "--hash", "--recursive", B2_REMOTE]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("HIBA az rclone futtatasa soran:", flush=True)
        print(result.stderr, flush=True)
        return []

    data = json.loads(result.stdout)
    with open(B2_LISTING_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"B2 listazas kesz: {len(data)} fajl. Mentve: {B2_LISTING_JSON}", flush=True)
    return data


def load_takeout_index_from_csv():
    """A mar elmentett takeout_teljes_index.csv-bol tolti vissza a sorokat,
    hogy ne kelljen ujra bejarni a Takeout mappat."""
    with open(TAKEOUT_INDEX_CSV, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    for row in rows:
        row["is_video"] = row["is_video"] in ("True", "true", "1")
    print(f"Takeout index betoltve gyorsitotarbol: {len(rows)} bejegyzes.", flush=True)
    return rows


def load_b2_listing_from_json():
    """A mar elmentett b2_kepek02_listing.json-bol tolti vissza a listat,
    hogy ne kelljen ujra lekerdezni rclone-nal."""
    with open(B2_LISTING_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"B2 listazas betoltve gyorsitotarbol: {len(data)} fajl.", flush=True)
    return data


# ---------------------------------------------------------------------------
# 3. lepes: osszefuzes SHA1 alapjan + elorejelzes vs valosag osszevetese
# ---------------------------------------------------------------------------

def main():
    use_cache = "--from-cache" in sys.argv

    if use_cache and os.path.exists(TAKEOUT_INDEX_CSV):
        takeout_rows = load_takeout_index_from_csv()
    else:
        takeout_rows = index_takeout()

    if not takeout_rows:
        print("Nincs mit egyeztetni, kilepek.")
        return

    if use_cache and os.path.exists(B2_LISTING_JSON):
        b2_files = load_b2_listing_from_json()
    else:
        b2_files = list_b2()
    b2_by_sha1 = {}
    for f in b2_files:
        h = (f.get("Hashes") or {}).get("sha1")
        if h:
            b2_by_sha1.setdefault(h.lower(), []).append(f["Path"])

    final_rows = []
    stats = {
        "egyezik": 0,
        "megtalalhato_de_mas_utvonalon": 0,
        "hianyzik_b2_rol": 0,
        "video_nincs_feltoltve_ahogy_varhato": 0,
        "video_megis_feltoltodott": 0,
    }

    for row in takeout_rows:
        sha1 = row["sha1"]
        actual_paths = b2_by_sha1.get(sha1, [])
        effective_date = datetime.strptime(row["effective_date"], "%Y-%m-%d %H:%M:%S")
        predicted = predict_b2_path(effective_date, row["filename"])

        if row["is_video"] == "True" or row["is_video"] is True:
            if not actual_paths:
                status = "video-nincs-feltoltve-ahogy-varhato"
                stats["video_nincs_feltoltve_ahogy_varhato"] += 1
            else:
                status = "video-megis-feltoltodott"
                stats["video_megis_feltoltodott"] += 1
        elif actual_paths:
            if predicted and predicted in actual_paths:
                status = "egyezik"
                stats["egyezik"] += 1
            else:
                status = "megtalalhato-de-mas-utvonalon"
                stats["megtalalhato_de_mas_utvonalon"] += 1
        else:
            status = "hianyzik-b2-rol"
            stats["hianyzik_b2_rol"] += 1

        final_rows.append({
            **row,
            "varhato_b2_utvonal": predicted or "",
            "tenyleges_b2_utvonalak": " | ".join(actual_paths),
            "statusz": status,
        })

    with open(FINAL_CSV, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(final_rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(final_rows)

    total = len(final_rows)
    summary_lines = [
        f"# Takeout <-> B2 teljes egyeztetes ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
        "",
        f"Osszes feldolgozott Takeout bejegyzes: **{total}**",
        "",
        "| Statusz | Darabszam |",
        "|---|---|",
    ]
    for k, v in stats.items():
        summary_lines.append(f"| {k} | {v} |")
    summary_lines += [
        "",
        f"Reszletes, soronkenti lista: `{os.path.basename(FINAL_CSV)}`",
        f"Nyers Takeout index: `{os.path.basename(TAKEOUT_INDEX_CSV)}`",
        f"Nyers B2 listazas: `{os.path.basename(B2_LISTING_JSON)}`",
    ]
    with open(SUMMARY_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print("\n--- KESZ ---")
    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()
