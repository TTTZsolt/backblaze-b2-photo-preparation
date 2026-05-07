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
    thumb_dir_name = "elokeszitett_thumbnails"
    target_dir_root = os.path.join(root_dir, target_dir_name)
    thumb_dir_root = os.path.join(root_dir, thumb_dir_name)
    
    # Thumbnail méret (a dokumentáció alapján 400px)
    thumb_size = (400, 400)
    
    # Engedélyezett képfájl kiterjesztések, kiegészítve HEIC/HEIF-fel
    valid_extensions = ('.jpg', '.jpeg', '.png', '.cr2', '.nef', '.heic', '.heif')
    
    print(f"--- Backblaze B2 Elokeszites inditasa v1.2 ---")
    print(f"Forras: {root_dir}")
    print(f"Cel:    {target_dir_root}")
    
    # HEIC támogatás inicializálása
    pillow_heif.register_heif_opener()
    
    # Bejárjuk a fájlrendszert
    processed_count = 0
    new_count = 0
    
    for subdir, dirs, files in os.walk(root_dir):
        # A célkönyvtárakat hagyjuk ki a keresésből, hogy ne rekurzáljunk bele
        if target_dir_name in subdir or "kepek02" in subdir or thumb_dir_name in subdir:
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
                
                final_thumb_dir = os.path.join(thumb_dir_root, clean_relative_path)
                final_thumb_path = os.path.join(final_thumb_dir, new_filename) # A thumbnail is JPG lesz vagy az eredeti kiterjesztés

                # Létrehozzuk a célmappákat, ha még nem léteznek
                for d in [final_target_dir, final_thumb_dir]:
                    if not os.path.exists(d):
                        try:
                            os.makedirs(d)
                        except OSError as e:
                            print(f"Hiba a mappa letrehozasakor ({d}): {e}")
                            continue

                processed_count += 1

                # Ha a nagy kép már megvan, mindent átugrunk
                if os.path.exists(final_target_path):
                    print(f"Atugorva (mar letezik): {os.path.join(clean_relative_path, new_filename)}")
                    continue
                
                new_count += 1
                
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

                # Fájl másolása vagy konvertálása ÉS Thumbnail készítés
                try:
                    old_path = os.path.join(subdir, filename)
                    
                    # 1. Eredeti (vagy konvertált) kép mentése (csak ha még nincs meg)
                    if not os.path.exists(final_target_path):
                        if is_heic:
                            with Image.open(old_path) as img:
                                img.convert('RGB').save(final_target_path, "JPEG", quality=95)
                            print(f"Konvertalva es masolva (HEIC->JPG): {os.path.join(clean_relative_path, new_filename)}")
                        else:
                            shutil.copy2(old_path, final_target_path)
                            print(f"Masolva: {os.path.join(clean_relative_path, new_filename)}")
                    else:
                        # Ha a nagy kép már megvan, csak csendben nyugtázzuk
                        pass

                    # 2. Thumbnail készítése (mindig JPG-be mentjük a hatékonyság érdekében)
                    # Ha a kiterjesztés nem .jpg, a final_thumb_path-ot korrigáljuk
                    if not final_thumb_path.lower().endswith(('.jpg', '.jpeg')):
                         thumb_name = os.path.splitext(new_filename)[0] + ".jpg"
                         final_thumb_path = os.path.join(final_thumb_dir, thumb_name)

                    if not os.path.exists(final_thumb_path):
                        with Image.open(old_path) as img:
                            # EXIF orientáció kezelése (fontos a thumbnailnél)
                            if hasattr(img, '_getexif'):
                                exif = img._getexif()
                                if exif:
                                    orientation = exif.get(0x0112)
                                    if orientation == 3: img = img.rotate(180, expand=True)
                                    elif orientation == 6: img = img.rotate(270, expand=True)
                                    elif orientation == 8: img = img.rotate(90, expand=True)
                            
                            img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                            if img.mode in ("RGBA", "P"):
                                img = img.convert("RGB")
                            img.save(final_thumb_path, "JPEG", quality=75, optimize=True)
                            print(f"  -> Thumbnail elkeszitve: {os.path.basename(final_thumb_path)}")
                except Exception as e:
                    print(f"Hiba a fajl feldolgozasa soran ({filename}): {e}")
            else:
                # Nem képfájl, csendben figyelmen kívül hagyjuk (vagy debug logolhatnánk)
                pass

    print("--- Lokalis elokeszites befejezodott! ---")
    
    # Rclone feltöltés indítása
    import subprocess
    print(f"\n--- Feltoltes inditasa a Backblaze B2-re (rclone) ---")
    remote_target = "b2_storage:Kepek02" # A távoli rclone cél (Figyelem: Kepek02 nagy K-val!)
    
    try:
        # A. Eredeti képek feltöltése
        print(f"1. Nagy kepek feltoltese...")
        cmd_main = ["rclone", "copy", target_dir_root, remote_target, "-v", "-P", "--update"]
        subprocess.run(cmd_main, check=True)
        
        # B. Thumbnail-ek feltöltése
        print(f"\n2. Thumbnail-ek feltoltese...")
        remote_thumbs = f"{remote_target.lower()}-thumbs"
        cmd_thumbs = ["rclone", "copy", thumb_dir_root, remote_thumbs, "-v", "-P", "--update"]
        subprocess.run(cmd_thumbs, check=True)
        
        print(f"\n--- Feltoltes sikeresen befejezodott! ---")
    except subprocess.CalledProcessError as e:
        print(f"\nHIBA: Az rclone futtatasa soran hiba tortent (kod: {e.returncode}).")
    except FileNotFoundError:
        print(f"\nHIBA: Az 'rclone' program nem talalhato a rendszerben.")
        print("Kerlek telepitsd az rclone-t, vagy ellenorizd a PATH beallitasokat!")

if __name__ == "__main__":
    prepare_b2_upload()
