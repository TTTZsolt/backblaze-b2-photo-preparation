"""
B2 datum-ellenorzo audit.

Megkeresi a Kepek02 vodorben mar fent levo fajlok kozott azokat, amelyeknek
a jelenlegi Ev/Honap mappaja NEM egyezik a fajlnevbol kiolvashato tenyleges
datummal (pl. "IMG_20211224_181930.jpg" a "2026/01/" mappaban - ez a
takeout_to_b2_feltoltes.py egy regi hibaja miatt tortenhetett, amikor egy
kepnek nem volt EXIF-datuma, es a script a ZIP-beli fajl-idobelyegre esett
vissza, ami a Takeout-export csomagolasi idejet tukrozi, nem a kep tenyleges
keszitesi datumat).

CSAK LISTAZ - semmit nem mozgat/torol a B2-n. A talalt gyanus fajlokat
kiirja a konzolra es egy CSV fajlba is menti.

Hasznalat:
    python audit_b2_dates.py
"""

import os
import re
import csv
import json
import sys
import subprocess
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REMOTE_PREFIX = "b2_storage"
TARGET_BUCKET = "Kepek02"
TARGET_REMOTE = f"{REMOTE_PREFIX}:{TARGET_BUCKET}"

YEAR_MONTH_PATH_RE = re.compile(r"^(\d{4})/(\d{2})/")

# Ugyanaz a fajlnev-datum felismero logika, mint a takeout_to_b2_feltoltes.py-ban.
FILENAME_DATETIME_RE = re.compile(r"(\d{4})(\d{2})(\d{2})[_-](\d{2})(\d{2})(\d{2})")
FILENAME_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def parse_date_from_filename(filename):
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


def list_b2_files():
    print(f"B2-tartalom listázása ({TARGET_REMOTE})...", flush=True)
    cmd = ["rclone", "lsjson", "--recursive", TARGET_REMOTE]
    result = subprocess.run(
        cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
    )
    if result.returncode != 0:
        print("HIBA az rclone lsjson futtatása során:", flush=True)
        print(result.stderr, flush=True)
        return []
    return json.loads(result.stdout)


def main():
    files = list_b2_files()
    print(f"Összesen {len(files)} fájl a vödörben.\n", flush=True)

    mismatches = []
    for f in files:
        path = f.get("Path", "")
        if f.get("IsDir"):
            continue
        m = YEAR_MONTH_PATH_RE.match(path)
        if not m:
            continue  # nem Ev/Honap mappastruktura - kihagyjuk
        folder_year, folder_month = int(m.group(1)), int(m.group(2))

        fname_date = parse_date_from_filename(path)
        if fname_date and (fname_date.year != folder_year or fname_date.month != folder_month):
            mismatches.append({
                "b2_utvonal": path,
                "jelenlegi_mappa": f"{folder_year}/{folder_month:02d}",
                "fajlnev_szerinti_datum": fname_date.strftime("%Y-%m-%d %H:%M:%S"),
                "javasolt_mappa": f"{fname_date.year}/{fname_date.month:02d}",
            })

    print(f"--- Gyanús eltérés: {len(mismatches)} db ---\n", flush=True)
    for row in mismatches:
        print(f"  {row['b2_utvonal']}", flush=True)
        print(f"    jelenlegi mappa: {row['jelenlegi_mappa']}  ->  "
              f"fájlnév szerint: {row['fajlnev_szerinti_datum']}  "
              f"(javasolt mappa: {row['javasolt_mappa']})", flush=True)

    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_csv = os.path.join(out_dir, "b2_datum_audit_eredmeny.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "b2_utvonal", "jelenlegi_mappa", "fajlnev_szerinti_datum", "javasolt_mappa"
        ])
        writer.writeheader()
        writer.writerows(mismatches)

    print(f"\nNapló mentve: {out_csv}", flush=True)
    print("\nEz a script CSAK LISTÁZOTT - semmit nem mozgatott/törölt a B2-n.", flush=True)


if __name__ == "__main__":
    main()
