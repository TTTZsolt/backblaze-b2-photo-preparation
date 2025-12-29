import os
import shutil
import unicodedata
import re

def clean_string(text):
    """
    Eltávolítja az ékezeteket, a nem angol karaktereket kötőjelre cseréli,
    és kisbetűssé alakítja a szöveget.
    """
    # 1. Ékezetek eltávolítása (Normalizálás)
    # Az 'NFD' szétbontja a karaktereket (pl. á -> a + ´), 
    # a 'Mn' kategória pedig a mellékjeleket jelöli, amiket eldobunk.
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    
    # 2. Minden átalakítása kisbetűssé
    text = text.lower()
    
    # 3. Speciális karakterek cseréje kötőjelre
    # Csak az angol ábécé betűit, számokat és a pontot hagyjuk meg (utóbbi a kiterjesztés miatt)
    # Minden mást (szóköz, írásjelek, perjelek) kötőjellé alakítunk.
    text = re.sub(r'[^a-z0-9.]', '-', text)
    
    # 4. Több egymás melletti kötőjel összevonása egyetlen kötőjellé
    text = re.sub(r'-+', '-', text)
    
    # 5. Felesleges kötőjelek levágása a szöveg elejéről és végéről
    text = text.strip('-')
    
    return text

def prepare_b2_upload():
    # A script abban a könyvtárban dolgozik, ahol elindították
    root_dir = os.getcwd()
    
    # Engedélyezett képfájl kiterjesztések
    valid_extensions = ('.jpg', '.jpeg', '.png', '.cr2', '.nef')
    
    print(f"--- Backblaze B2 Elokeszites inditasa: {root_dir} ---")
    
    # Bejárjuk a fájlrendszert
    # Az os.walk() visszaadja az aktuális mappát (root), az alkönyvtárakat (dirs) és a fájlokat (files)
    for subdir, dirs, files in os.walk(root_dir):
        # 1. Először megkeressük a mappában az összes "-szerkesztve" végű fájlt
        # Ez azért kell, hogy tudjuk, melyik eredeti fájlokat kell majd átugrani
        edited_bases = set()
        for f in files:
            name, ext = os.path.splitext(f)
            if name.lower().endswith("-szerkesztve"):
                # Levágjuk a "-szerkesztve" (12 karakter: kötőjel + 11 betű) részt az alapnévből
                base = name.lower()[:-12]
                edited_bases.add(base)

        for filename in files:
            # Csak a megadott kiterjesztésű fájlokkal foglalkozunk
            if filename.lower().endswith(valid_extensions):
                
                # Meghatározzuk a fájl relatív útját a főkönyvtárhoz képest
                relative_path = os.path.relpath(subdir, root_dir)
                
                # Szétválasztjuk a fájlnevet és a kiterjesztést a tisztításhoz
                name_part, extension_part = os.path.splitext(filename)
                
                # 2. Ellenőrizzük, hogy van-e szerkesztett változata ennek a fájlnak
                # Ha van, akkor az eredetit átugorjuk
                if name_part.lower() in edited_bases:
                    print(f"Atugorva (van szerkesztett valtozat): {filename}")
                    continue

                extension_part = extension_part.lower() # A kiterjesztés is legyen kisbetűs
                
                # Új név generálása
                if relative_path == ".":
                    # Ha a fájl a főkönyvtárban (root) van
                    new_name_base = clean_string(name_part)
                else:
                    # Ha alkönyvtárban van: [RelatívÚt]--[Fájlnév]
                    clean_path = clean_string(relative_path)
                    clean_name = clean_string(name_part)
                    new_name_base = f"{clean_path}--{clean_name}"
                
                new_filename = f"{new_name_base}{extension_part}"
                
                # Teljes elérési utak
                old_path = os.path.join(subdir, filename)
                new_path = os.path.join(root_dir, new_filename)
                
                # Ha a fájl már a helyén van és jó a neve, ne csináljunk semmit
                if old_path == new_path:
                    continue

                # Ha a célfájl már létezik, átugorjuk a feldolgozást
                # Ez lehetővé teszi, hogy a scriptet többször is lefuttassuk
                if os.path.exists(new_path):
                    print(f"Atugorva (mar letezik): {new_filename}")
                    continue

                # Fájl másolása (átnevezéssel együtt)
                # A shutil.copy2 megőrzi a fájl eredeti metaadatait (pl. készítés dátuma)
                try:
                    shutil.copy2(old_path, new_path)
                    # A print-nél az eredeti nevet is tisztítjuk a biztonság kedvéért a konzolon
                    print(f"Masolva: {new_filename}")
                except Exception as e:
                    print(f"Hiba a fajl masolasa soran: {e}")

    print("--- Folyamat befejezodott! ---")

if __name__ == "__main__":
    prepare_b2_upload()
