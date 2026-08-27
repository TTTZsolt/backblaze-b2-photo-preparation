"""
B2 datum-javito eszkoz (3. fazis - kategoria-besorolasok atvitele).

A fix_b2_dates.py altal letrehozott b2_move_terkep.csv (regi_utvonal,
uj_utvonal parok) alapjan atvezeti a media_classifications tabla sorait
a regi fajlnevrol az ujra, HOGY A MAR MEGLEVO KATEGORIA-BESOROLAS NE
VESSZEN EL a kovetkezo B2-szinkronizalaskor.

Ezt a szkriptet a TABLETEN kell futtatni, a valódi, eles photos_app.db
ellen (nem a Lenovo-n levo fejlesztoi peldanyon), mert ott vannak a
tenyleges kategoria-besorolasok.

Alapertelmezetten DRY-RUN: csak kiirja, mit valtoztatna, semmit nem ir
az adatbazisba. Tenyleges vegrehajtashoz: --execute

Hasznalat (a tableten, a swift-newton konyvtarban, ahol a photos_app.db
van):
    python fix_classifications_db.py --map b2_move_terkep.csv
    python fix_classifications_db.py --map b2_move_terkep.csv --execute
"""

import argparse
import csv
import os
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_mapping(csv_path):
    pairs = []
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pairs.append((row["regi_utvonal"], row["uj_utvonal"]))
    return pairs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", default="b2_move_terkep.csv",
                         help="A fix_b2_dates.py altal irt mozgatas-terkep CSV utvonala")
    parser.add_argument("--db", default="photos_app.db",
                         help="A photos_app.db elerese utvonala")
    parser.add_argument("--execute", action="store_true",
                         help="Tenyleges DB-irasa (alapertelmezes: dry-run)")
    args = parser.parse_args()

    execute = args.execute
    mode_label = "TÉNYLEGES VÉGREHAJTÁS" if execute else "DRY-RUN (semmi nem íródik)"
    print(f"--- Kategória-átvitel ({mode_label}) ---")
    print(f"Térkép: {args.map}")
    print(f"Adatbázis: {args.db}\n")

    if not os.path.exists(args.db):
        print(f"HIBA: nem található az adatbázis: {args.db}")
        sys.exit(1)

    pairs = load_mapping(args.map)
    print(f"{len(pairs)} fájl-pár a térképben.\n")

    conn = sqlite3.connect(args.db)
    cur = conn.cursor()

    renamed = 0
    merged = 0
    skipped_no_old = 0
    flagged_renamed = 0

    for old_path, new_path in pairs:
        cur.execute("SELECT category, is_deleted, ai_suggested_category, ai_status, ai_error "
                    "FROM media_classifications WHERE file_name = ?", (old_path,))
        old_row = cur.fetchone()

        if old_row is None:
            skipped_no_old += 1
        else:
            cur.execute("SELECT 1 FROM media_classifications WHERE file_name = ?", (new_path,))
            new_exists = cur.fetchone() is not None

            if new_exists:
                category, is_deleted, ai_suggested_category, ai_status, ai_error = old_row
                print(f"  [ÖSSZEVONÁS] {old_path}\n              -> {new_path}"
                      f"  (kategória: {category})")
                merged += 1
                if execute:
                    cur.execute(
                        "UPDATE media_classifications SET category=?, is_deleted=?, "
                        "ai_suggested_category=?, ai_status=?, ai_error=? WHERE file_name=?",
                        (category, is_deleted, ai_suggested_category, ai_status, ai_error, new_path),
                    )
                    cur.execute("DELETE FROM media_classifications WHERE file_name=?", (old_path,))
            else:
                category = old_row[0]
                print(f"  [ÁTNEVEZÉS] {old_path}\n             -> {new_path}  (kategória: {category})")
                renamed += 1
                if execute:
                    cur.execute(
                        "UPDATE media_classifications SET file_name=? WHERE file_name=?",
                        (new_path, old_path),
                    )

        cur.execute("SELECT 1 FROM flagged_images WHERE file_name = ?", (old_path,))
        if cur.fetchone() is not None:
            flagged_renamed += 1
            print(f"  [FLAG ÁTNEVEZÉS] {old_path} -> {new_path}")
            if execute:
                cur.execute(
                    "UPDATE flagged_images SET file_name=? WHERE file_name=?",
                    (new_path, old_path),
                )

    if execute:
        conn.commit()
    conn.close()

    print(f"\nÖsszegzés: {renamed} átnevezve, {merged} összevonva, "
          f"{skipped_no_old} kihagyva (nem volt kategóriájuk), "
          f"{flagged_renamed} flagged_images sor érintve.")

    if not execute:
        print("\nEz DRY-RUN volt - az adatbázisba semmi nem íródott.")
        print("Tényleges végrehajtáshoz: python fix_classifications_db.py --map ... --execute")


if __name__ == "__main__":
    main()
