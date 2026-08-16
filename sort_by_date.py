import os
import re
import sys
import shutil
import hashlib
import argparse
import unicodedata
from datetime import datetime
from collections import defaultdict
from PIL import Image
from PIL.ExifTags import TAGS

import pillow_heif

# HEIC támogatás inicializálása
pillow_heif.register_heif_opener()

# A Windows konzol nem mindig tudja kiirni az ekezetes karaktereket -
# UTF-8 kimenetet kenyszeritunk, hogy ne alljon le emiatt a script.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Album-mappanev alapu celutvonal-szamitas
# Lasd: mappazasi_algoritmus_specifikacio.md
# ---------------------------------------------------------------------------

DAY_ALBUM_RE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})[ _](.+)$")
YEAR_ALBUM_RE = re.compile(r"^(\d{4})[ _](.+)$")
GENERIC_WORDS = ("fotói", "fotoi", "photos", "videói", "videoi")


def clean_string(text):
    """Azonos a prepare_photos.py clean_string() fuggvenyevel."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9.]", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


def get_creation_date(file_path):
    """
    Megpróbálja kinyerni a fénykép készítésének idejét az EXIF adatokból.
    Ha nem sikerül, a fájl módosítási idejét adja vissza.
    """
    try:
        img = Image.open(file_path)
        exif_data = img._getexif()
        if exif_data:
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                if tag_name == "DateTimeOriginal":
                    try:
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
    except Exception:
        pass

    mtime = os.path.getmtime(file_path)
    return datetime.fromtimestamp(mtime)


def sha1_of_file(path, chunk_size=1024 * 1024):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def match_named_album(folder_name):
    """Megprobalja felismerni, hogy a mappanev egy nevesitett Google Fotok
    album-e (nem az altalanos evenkenti gyujtomappa). Visszaad egy
    ('day', (ev, honap, nap, esemeny_szoveg)) vagy ('year', (ev, esemeny_szoveg))
    tuple-t, vagy None-t, ha nem album (pl. az altalanos gyujtomappa)."""
    m = DAY_ALBUM_RE.match(folder_name)
    if m:
        return ("day", m.groups())

    m = YEAR_ALBUM_RE.match(folder_name)
    if m:
        year, evname = m.groups()
        low = evname.lower().strip()
        if any(w in low for w in GENERIC_WORDS):
            return None
        return ("year", (year, evname))

    return None


def compute_target_subpath(dt, album_match, filename):
    """A specifikacio 2.2/2.3 pontja szerinti celutvonal (target_root-hoz
    kepesti relativ utvonal) kiszamitasa."""
    name, ext = os.path.splitext(filename)
    clean_name = clean_string(name)
    ext = ext.lower()

    if album_match:
        kind, groups = album_match
        evname = groups[3] if kind == "day" else groups[1]
        evname_clean = clean_string(evname)
        sub = f"{dt.day:02d}-{evname_clean}" if evname_clean else f"{dt.day:02d}"
        return os.path.join(f"{dt.year:04d}", f"{dt.month:02d}", sub, f"{clean_name}{ext}")

    return os.path.join(f"{dt.year:04d}", f"{dt.month:02d}", f"{clean_name}{ext}")


# ---------------------------------------------------------------------------
# Fo folyamat
# ---------------------------------------------------------------------------

def sort_photos(source_dir, target_root, dry_run=False):
    valid_extensions = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".cr2", ".nef")

    if not os.path.exists(source_dir):
        print(f"HIBA: A forrás könyvtár nem létezik: {source_dir}")
        print("TIPP: Ha szóköz van az útvonalban, tedd idézőjelek közé!")
        return

    print("--- Fényképek szortírozása indult (album-felismeréssel) ---")
    print(f"Forrás: {source_dir}")
    print(f"Cél:    {target_root}")
    if dry_run:
        print("!!! DRY-RUN MOD: semmi nem lesz ténylegesen mozgatva/törölve, csak kiírva. !!!")

    # --- 1. lepes: teljes bejaras, tartalom (SHA1) szerinti csoportositas ---
    print("\n--- 1. lépés: fájlok indexelése (tartalom-hash alapján) ---")
    by_hash = defaultdict(list)  # sha1 -> [(full_path, parent_folder_name, filename), ...]
    scanned = 0
    for root, dirs, files in os.walk(source_dir):
        parent_name = os.path.basename(root)
        for filename in files:
            if not filename.lower().endswith(valid_extensions):
                continue
            full_path = os.path.join(root, filename)
            try:
                h = sha1_of_file(full_path)
            except Exception as e:
                print(f"  [Hash hiba] {full_path}: {e}")
                continue
            by_hash[h].append((full_path, parent_name, filename))
            scanned += 1
            if scanned % 200 == 0:
                print(f"  ... {scanned} fájl indexelve", flush=True)

    named_album_count = sum(
        1 for occs in by_hash.values() if any(match_named_album(p) for _, p, _ in occs)
    )
    print(f"Indexelés kész: {scanned} fájl, {len(by_hash)} egyedi tartalom "
          f"({named_album_count} nevesített albumban is megtalálható).")

    # --- 2. lepes: celutvonal szamitas + mozgatas / duplikatum-torles ---
    print("\n--- 2. lépés: célútvonal számítás és mozgatás ---")
    moved = 0
    duplicates_removed = 0
    already_at_target = 0

    for h, occurrences in by_hash.items():
        chosen_path = None
        chosen_filename = None
        chosen_album_match = None
        for full_path, parent_name, filename in occurrences:
            m = match_named_album(parent_name)
            if m:
                chosen_path, chosen_filename, chosen_album_match = full_path, filename, m
                break
        if chosen_path is None:
            chosen_path, _, chosen_filename = occurrences[0]
            chosen_album_match = None

        dt = get_creation_date(chosen_path)
        rel_target = compute_target_subpath(dt, chosen_album_match, chosen_filename)
        dest_path = os.path.join(target_root, rel_target)
        dest_dir = os.path.dirname(dest_path)

        if os.path.exists(dest_path):
            already_at_target += 1
            if not dry_run:
                for p, _, _ in occurrences:
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            continue

        if dry_run:
            print(f"  [DRY-RUN] {chosen_path}\n            -> {dest_path}")
            moved += 1
            continue

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        try:
            shutil.move(chosen_path, dest_path)
            moved += 1
        except Exception as e:
            print(f"  [Mozgatási hiba] {chosen_path} -> {dest_path}: {e}")
            continue

        for p, _, _ in occurrences:
            if p == chosen_path:
                continue
            try:
                os.remove(p)
                duplicates_removed += 1
            except Exception:
                pass

    print("\n--- Kész! ---")
    print(f"Áthelyezve: {moved}")
    print(f"Már a célon volt (forrás-duplikátum törölve): {already_at_target}")
    print(f"Egyéb, ugyanazon tartalmú duplikátum törölve: {duplicates_removed}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fényképek szortírozása dátum és Google Fotók album-név alapján."
    )
    parser.add_argument("source", help="A feldolgozandó képeket tartalmazó könyvtár útvonala.")
    parser.add_argument(
        "-r", "--recursive", action="store_true",
        help="(Elavult kapcsoló, megtartva kompatibilitás miatt - a bejárás mindig teljes körű, "
             "mert az album-felismeréshez a teljes fastruktúra szükséges.)"
    )
    parser.add_argument(
        "--target", default=r"c:\Users\zsolt.tuske\Pictures\Véglegesített képek",
        help="Cél gyökérkönyvtár (alapértelmezett: Véglegesített képek)."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Csak kiírja, mit tenne, ténylegesen nem mozgat/töröl semmit. "
             "ELSŐ FUTTATÁSKOR ERŐSEN AJÁNLOTT!"
    )

    if len(sys.argv) > 2 and not sys.argv[1].startswith("-"):
        print("FIGYELEM: Úgy tűnik, szóköz van az útvonalban idézőjelek nélkül!")
        print("Példa a helyes használatra:")
        print(f'python sort_by_date.py "{ " ".join([a for a in sys.argv[1:] if not a.startswith("-")]) }"')
        print("-" * 40)

    args = parser.parse_args()
    source_dir = args.source.strip().strip('"')
    sort_photos(source_dir, args.target, dry_run=args.dry_run)
