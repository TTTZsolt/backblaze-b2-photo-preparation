import os
import shutil
import argparse
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS

import pillow_heif

# HEIC támogatás inicializálása
pillow_heif.register_heif_opener()

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
                    # Formátum: "YYYY:MM:DD HH:MM:SS"
                    try:
                        return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        continue
    except Exception:
        # Ha nem tudjuk megnyitni vagy nincs EXIF, megyünk tovább
        pass
    
    # Fallback: fájl módosítási ideje
    mtime = os.path.getmtime(file_path)
    return datetime.fromtimestamp(mtime)

def sort_photos(source_dir, recursive=False):
    target_root = r"c:\Users\zsolt.tuske\Pictures\Véglegesített képek"
    valid_extensions = ('.jpg', '.jpeg', '.png', '.heic', '.heif', '.cr2', '.nef')
    
    if not os.path.exists(source_dir):
        print(f"HIBA: A forrás könyvtár nem létezik: {source_dir}")
        print("TIPP: Ha szóköz van az útvonalban, tedd idézőjelek közé!")
        return

    print(f"--- Fényképek szortírozása indult ---")
    print(f"Forrás: {source_dir}")
    print(f"Cél:    {target_root}")

    count = 0
    
    # Bejárjuk a mappát
    for root, dirs, files in os.walk(source_dir):
        # Ha nem rekurzív, csak az első szintet nézzük
        if not recursive and root != source_dir:
            continue
            
        for filename in files:
            file_path = os.path.join(root, filename)
            
            # Ellenőrizzük a kiterjesztést
            if filename.lower().endswith(valid_extensions):
                dt = get_creation_date(file_path)
                
                year = dt.strftime("%Y")
                month = dt.strftime("%m")
                
                # Cél mappa felépítése
                dest_dir = os.path.join(target_root, year, month)
                dest_path = os.path.join(dest_dir, filename)
                
                # Mappák létrehozása ha nem léteznek
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir)
                    print(f"Mappa létrehozva: {dest_dir}")
                
                # Fájl mozgatása
                try:
                    # Ha a célfájl már létezik, ne írjuk felül (biztonság)
                    if os.path.exists(dest_path):
                        os.remove(file_path)
                        print(f"Törölve (már létezik a célhelyen): {filename}")
                        count += 1
                    else:
                        shutil.move(file_path, dest_path)
                        print(f"Mozgatva: {filename} -> {year}/{month}/")
                        count += 1
                except Exception as e:
                    print(f"Hiba a mozgatás során ({filename}): {e}")

    print(f"--- Kész! {count} fájl lett feldolgozva. ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fényképek szortírozása dátum szerint.")
    parser.add_argument("source", help="A feldolgozandó képeket tartalmazó könyvtár útvonala.")
    parser.add_argument("-r", "--recursive", action="store_true", help="Almappák tartalmának feldolgozása is.")
    
    # Külön kezeljük, ha a felhasználó elfelejtette az idézőjeleket
    import sys
    if len(sys.argv) > 2 and not sys.argv[1].startswith("-"):
        print("FIGYELEM: Úgy tűnik, szóköz van az útvonalban idézőjelek nélkül!")
        print("Példa a helyes használatra:")
        print(f'python sort_by_date.py "{ " ".join([arg for arg in sys.argv[1:] if not arg.startswith("-")]) }"')
        print("-" * 40)

    args = parser.parse_args()
    source_dir = args.source.strip().strip('"')
    sort_photos(source_dir, args.recursive)
