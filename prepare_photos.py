import os
import shutil
import unicodedata
import re
from PIL import Image
import pillow_heif

def clean_string(text):
    """
    Eltávolítja az ékezeteket, a nem angol karaktereket kötőjelre cseréli,
    és kisbetűssé alakítja a szöveget.
    """
    # 1. Ékezetek eltávolítása (Normalizálás)
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    
    # 2. Minden átalakítása kisbetűssé
    text = text.lower()
    
    # 3. Speciális karakterek cseréje kötőjelre
    # Csak az angol ábécé betűit, számokat és a pontot hagyjuk meg
    text = re.sub(r'[^a-z0-9.]', '-', text)
    
    # 4. Több egymás melletti kötőjel összevonása egyetlen kötőjellé
    text = re.sub(r'-+', '-', text)
    
    # 5. Felesleges kötőjelek levágása a szöveg elejéről és végéről
    text = text.strip('-')
    
    return text

def prepare_b2_upload():
    # A script abban a könyvtárban dolgozik, ahol elindították
    root_dir = os.getcwd()
    target_dir_name = "elokeszitett_kepek"
    target_dir_root = os.path.join(root_dir, target_dir_name)
    
    # Engedélyezett képfájl kiterjesztések, kiegészítve HEIC/HEIF-fel
    valid_extensions = ('.jpg', '.jpeg', '.png', '.cr2', '.nef', '.heic', '.heif')
    
    print(f"--- Backblaze B2 Elokeszites inditasa v1.2 ---")
    print(f"Forras: {root_dir}")
    print(f"Cel:    {target_dir_root}")
    
    # HEIC támogatás inicializálása
    pillow_heif.register_heif_opener()
    
    # Bejárjuk a fájlrendszert
    for subdir, dirs, files in os.walk(root_dir):
        # A célkönyvtárat magát hagyjuk ki a keresésből, hogy ne rekurzáljunk bele
        if target_dir_name in subdir:
            continue

        # 1. Először megkeressük a mappában az összes "-szerkesztve" végű fájlt
        edited_bases = set()
        for f in files:
            name, ext = os.path.splitext(f)
            if name.lower().endswith("-szerkesztve"):
                base = name.lower()[:-12] # "-szerkesztve" levágása
                edited_bases.add(base)

        for filename in files:
            # CSAK a megadott kiterjesztésű fájlokkal foglalkozunk (Képek szűrése)
            if filename.lower().endswith(valid_extensions):
                
                # Meghatározzuk a relatív útvonalat
                # pl. "Képek/2023/Nyár" -> "kepek/2023/nyar" (tisztítva)
                relative_path = os.path.relpath(subdir, root_dir)
                
                if relative_path == ".":
                     # Ha a fájl a főkönyvtárban van, akkor közvetlenül a célmappába kerül
                    clean_relative_path = ""
                else:
                    # Feldaraboljuk az útvonalat és minden elemet külön tisztítunk
                    path_parts = relative_path.split(os.sep)
                    clean_parts = [clean_string(part) for part in path_parts]
                    clean_relative_path = os.path.join(*clean_parts)
                
                # Szétválasztjuk a fájlnevet és a kiterjesztést
                name_part, extension_part = os.path.splitext(filename)
                
                # Ellenőrizzük, hogy van-e szerkesztett változata
                if name_part.lower() in edited_bases:
                    print(f"Atugorva (van szerkesztett valtozat): {filename}")
                    continue

                clean_name = clean_string(name_part)
                extension_part = extension_part.lower()
                
                # HEIC fájlok konvertálása JPG-be, így a cél kiterjesztés jpg lesz
                is_heic = extension_part in ('.heic', '.heif')
                target_extension = '.jpg' if is_heic else extension_part
                
                new_filename = f"{clean_name}{target_extension}"
                
                # Cél elérése
                # Teljes struktúra: target_dir / cleaned_subdirs / cleaned_filename
                final_target_dir = os.path.join(target_dir_root, clean_relative_path)
                final_target_path = os.path.join(final_target_dir, new_filename)
                
                # Létrehozzuk a célmappát, ha még nem létezik
                if not os.path.exists(final_target_dir):
                    try:
                        os.makedirs(final_target_dir)
                    except OSError as e:
                        print(f"Hiba a mappa letrehozasakor ({final_target_dir}): {e}")
                        continue

                # Ha a fájl már létezik, átugorjuk
                if os.path.exists(final_target_path):
                    print(f"Atugorva (mar letezik): {os.path.join(clean_relative_path, new_filename)}")
                    continue
                
                # Ütközéskezelés (bár a mappastruktúra miatt ritkább, de lehetséges)
                # Ha véletlenül két fájl neve tisztítva ugyanaz lenne ugyanabban a mappában
                counter = 1
                base_target_path = final_target_path
                while os.path.exists(final_target_path):
                     # Ez a ciklus technikailag az előző "skip" miatt nem fut le jelen formában,
                     # de meghagyjuk a logikát arra az esetre, ha a jövőben változtatnánk a "skip" szabályon.
                     # Jelenleg a "skip" erősebb.
                     pass 
                     # (A fenti skip miatt ez a rész most nem releváns, de a robusztusság kedvéért
                     #  kivehetjük a skip-et, ha felülírást vagy verziózást akarunk. Most marad a skip.)

                # Fájl másolása vagy konvertálása
                try:
                    old_path = os.path.join(subdir, filename)
                    if is_heic:
                        # HEIC megnyitása és mentése JPG-ként
                        with Image.open(old_path) as img:
                            # A HEIC EXIF orientációjának alkalmazása, ha van, és konvertálás RGB-be
                            img.convert('RGB').save(final_target_path, "JPEG", quality=95)
                        print(f"Konvertalva es masolva (HEIC->JPG): {os.path.join(clean_relative_path, new_filename)}")
                    else:
                        shutil.copy2(old_path, final_target_path)
                        print(f"Masolva: {os.path.join(clean_relative_path, new_filename)}")
                except Exception as e:
                    print(f"Hiba a fajl feldolgozasa soran ({filename}): {e}")
            else:
                # Nem képfájl, csendben figyelmen kívül hagyjuk (vagy debug logolhatnánk)
                pass

    print("--- Folyamat befejezodott! ---")

if __name__ == "__main__":
    prepare_b2_upload()
