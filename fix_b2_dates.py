"""
B2 datum-javito eszkoz (2. fazis - a tenyleges mozgatas).

Az audit_b2_dates.py altal talalt, hibas Ev/Honap mappaba kerult fajlokat
athelyezi a B2-n (Kepek02 vodor) a fajlnev alapjan helyes Ev/Honap mappaba.
Ha letezik hozza tartozo thumbnail a Kepek02-thumbs vodorben, azt is athelyezi.

FONTOS: ez a script CSAK a B2-t modositja. A Lumina alkalmazas sajat
adatbazisaban (media_classifications) a fajlhoz esetleg mar hozzarendelt
kategoria emiatt "arvava" valhat a kovetkezo B2-szinkronizalasnal, mert a
worker.py ujra epiti a media_items tablat, es torli azokat a
media_classifications sorokat, amiknek a fajlneve mar nem szerepel benne.

--> A media_classifications athozatalat KULON, a tableten (az eles
adatbazison) futtatando szkript vegzi (lasd: fix_classifications_db.py),
MIUTAN ez a script mar lefutott es letrehozta a mozgatas-terkepet
(b2_move_terkep.csv).

Alapertelmezetten DRY-RUN: csak kiirja, mit MOZGATNA, semmit nem mozgat.
Tenyleges mozgatashoz: python fix_b2_dates.py --execute
"""

import os
import re
import csv
import sys
import json
import argparse
import subprocess
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REMOTE = "b2_storage:Kepek02"
THUMBS_REMOTE = "b2_storage:kepek02-thumbs"

YEAR_MONTH_PATH_RE = re.compile(r"^(\d{4})/(\d{2})/")
FILENAME_DATETIME_RE = re.compile(r"(\d{4})(\d{2})(\d{2})[_-](\d{2})(\d{2})(\d{2})")
FILENAME_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAP_CSV = os.path.join(SCRIPT_DIR, "b2_move_terkep.csv")


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


def list_remote_files(remote):
    cmd = ["rclone", "lsjson", "--recursive", remote]
    result = subprocess.run(
        cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
    )
    if result.returncode != 0:
        print(f"HIBA az rclone lsjson futtatása során ({remote}):")
        print(result.stderr)
        return []
    return json.loads(result.stdout)


def find_mismatches():
    files = list_remote_files(REMOTE)
    mismatches = []
    for f in files:
        path = f.get("Path", "")
        if f.get("IsDir"):
            continue
        m = YEAR_MONTH_PATH_RE.match(path)
        if not m:
            continue
        folder_year, folder_month = int(m.group(1)), int(m.group(2))
        fname_date = parse_date_from_filename(path)
        if fname_date and (fname_date.year != folder_year or fname_date.month != folder_month):
            new_path = re.sub(
                r"^\d{4}/\d{2}/",
                f"{fname_date.year}/{fname_date.month:02d}/",
                path,
            )
            mismatches.append((path, new_path))
    return mismatches


def move_one(remote, old_path, new_path, execute):
    old_full = f"{remote}/{old_path}"
    new_full = f"{remote}/{new_path}"
    if not execute:
        print(f"    [DRY-RUN] {remote.split(':')[-1]}: {old_path}  ->  {new_path}")
        return True
    cmd = ["rclone", "moveto", old_full, new_full]
    result = subprocess.run(
        cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
    )
    if result.returncode != 0:
        print(f"    [HIBA] {remote.split(':')[-1]}: {old_path} -> {new_path}")
        print(f"      {result.stderr.strip()}")
        return False
    print(f"    [OK] {remote.split(':')[-1]}: {old_path}  ->  {new_path}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true",
                         help="Tenyleges mozgatas vegrehajtasa (alapertelmezes: dry-run)")
    args = parser.parse_args()

    execute = args.execute
    mode_label = "TÉNYLEGES MOZGATÁS" if execute else "DRY-RUN (semmi nem mozdul)"
    print(f"--- B2 dátum-javító ({mode_label}) ---\n")

    mismatches = find_mismatches()
    print(f"{len(mismatches)} javítandó fájl.\n")

    # Melyik thumbnail-ek leteznek egyaltalan? (egy lekerdezessel, ne fajlonkent)
    thumb_files = list_remote_files(THUMBS_REMOTE)
    thumb_paths = {f["Path"] for f in thumb_files if not f.get("IsDir")}

    successful_moves = []
    for old_path, new_path in mismatches:
        print(f"  {old_path}")
        ok = move_one(REMOTE, old_path, new_path, execute)
        if ok:
            successful_moves.append((old_path, new_path))
        if old_path in thumb_paths:
            move_one(THUMBS_REMOTE, old_path, new_path, execute)
        print()

    with open(MAP_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["regi_utvonal", "uj_utvonal"])
        writer.writerows(successful_moves)

    print(f"Mozgatás-térkép mentve: {MAP_CSV}")
    if not execute:
        print("\nEz DRY-RUN volt - semmi nem mozdult a B2-n.")
        print("Tényleges mozgatáshoz: python fix_b2_dates.py --execute")
    else:
        print("\nFONTOS KÖVETKEZŐ LÉPÉS:")
        print("A media_classifications táblában lévő kategória-besorolások")
        print("átvitele a tablet éles adatbázisán a fix_classifications_db.py")
        print(f"szkripttel történik, a most létrejött {os.path.basename(MAP_CSV)} alapján.")


if __name__ == "__main__":
    main()
