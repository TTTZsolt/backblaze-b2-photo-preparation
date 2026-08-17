"""
Ellenorzi azt a hipotezist, hogy a B2-n talalhato, az egyszeru EXIF-Ev/Honap
elorejelzestol elutero utvonalak megmagyarazhatok-e a Takeout-beli, nevvel
ellatott Google Fotok album-mappa nevebol (pl. "2012_09_08 Esemeny neve").
"""

import os
import re
import csv
import unicodedata
from collections import defaultdict
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
FINAL_CSV = os.path.join(BASE, "takeout_b2_teljes_egyeztetes.csv")


def clean_string(text):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9.]", "-", text)
    text = re.sub(r"-+", "-", text)
    text = text.strip("-")
    return text


DAY_ALBUM_RE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})[ _](.+)$")
YEAR_ALBUM_RE = re.compile(r"^(\d{4})[ _](.+)$")
GENERIC_WORDS = ("fotói", "fotoi", "photos", "videói", "videoi")


def album_folder_from_internal_path(internal_path):
    parts = internal_path.replace("\\", "/").split("/")
    if len(parts) < 2:
        return None
    return parts[-2]


def predict_from_album(album, filename, exif_year=None, exif_month=None, exif_day=None):
    """Tobb jelolt utvonalat ad vissza (list). Az album mappanev sajat
    datum-resze nem mindig megbizhato (elofordul, hogy a felhasznalo
    tevedett a honap/ev megadasakor) - ezert az EXIF-bol szarmazo
    ev/honap/nap alapu jelolteket IS megprobaljuk, csak az esemeny-nevet
    hasznalva az album mappanevbol."""
    name, ext = os.path.splitext(filename)
    clean_name = clean_string(name)
    ext = ext.lower()
    if ext in (".heic", ".heif"):
        ext = ".jpg"

    candidates = []

    m = DAY_ALBUM_RE.match(album)
    if m:
        year, month, day, evname = m.groups()
        with_day = clean_string(f"{day} {evname}")
        without_day = clean_string(evname)
        full_flat = clean_string(album)
        candidates.append(f"{year}/{month}/{with_day}/{clean_name}{ext}")
        candidates.append(f"{year}/{month}/{without_day}/{clean_name}{ext}")
        candidates.append(f"{year}/{month}/{full_flat}/{clean_name}{ext}")

        if exif_year and exif_month and exif_day:
            exif_with_day = clean_string(f"{exif_day:02d} {evname}")
            candidates.append(f"{exif_year}/{exif_month:02d}/{exif_with_day}/{clean_name}{ext}")
            candidates.append(f"{exif_year}/{exif_month:02d}/{without_day}/{clean_name}{ext}")
        return candidates

    m = YEAR_ALBUM_RE.match(album)
    if m:
        year, evname = m.groups()
        low = evname.lower().strip()
        if any(w in low for w in GENERIC_WORDS):
            return []
        sub = clean_string(f"{year} {evname}")
        candidates.append(f"{year}/{sub}/{clean_name}{ext}")
        if exif_year:
            sub_exif = clean_string(f"{exif_year} {evname}")
            candidates.append(f"{exif_year}/{sub_exif}/{clean_name}{ext}")
        return candidates

    return []


def main():
    with open(FINAL_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    by_sha1 = defaultdict(list)
    for r in rows:
        by_sha1[r["sha1"]].append(r)

    mismatched_groups = 0
    explained = 0
    unexplained = []

    for sha1, group in by_sha1.items():
        actual = None
        for r in group:
            if r["tenyleges_b2_utvonalak"]:
                actual = r["tenyleges_b2_utvonalak"].split(" | ")[0]
                break
        if not actual:
            continue  # nincs B2 talalat ehhez a tartalomhoz, kihagyjuk

        naive_match = any(r["varhato_b2_utvonal"] == actual for r in group)
        if naive_match:
            continue

        mismatched_groups += 1

        found = False
        for r in group:
            album = album_folder_from_internal_path(r["internal_path"])
            if not album:
                continue
            try:
                dt = datetime.strptime(r["effective_date"], "%Y-%m-%d %H:%M:%S")
                ey, em, ed = dt.year, dt.month, dt.day
            except Exception:
                ey = em = ed = None
            for pred in predict_from_album(album, r["filename"], ey, em, ed):
                if pred == actual:
                    found = True
                    break
            if found:
                break

        if found:
            explained += 1
        elif len(unexplained) < 15:
            unexplained.append((sha1, actual, [r["internal_path"] for r in group]))

    print(f"Osszes elemzett SHA1-csoport (van B2 talalat, de nem naiv egyezes): {mismatched_groups}")
    if mismatched_groups:
        pct = 100 * explained / mismatched_groups
        print(f"Album-nev alapjan megmagyarazhato: {explained} ({pct:.1f}%)")
        print(f"Nem magyarazhato ezzel a hipotezissel: {mismatched_groups - explained}")
    print()
    print("Minta a MEG NEM magyarazott esetekre (max 15):")
    for sha1, actual, paths in unexplained:
        print(f"  SHA1={sha1[:10]}...  tenyleges={actual}")
        for p in paths:
            print(f"    takeout: {p}")


if __name__ == "__main__":
    main()
