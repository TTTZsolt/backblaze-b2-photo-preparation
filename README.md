# Fénykép Kezelő Eszközök (Backblaze B2 előkészítés)

Ez a repository két fő eszközt tartalmaz a fényképek rendszerezéséhez és felhőbe (Backblaze B2) való feltöltésének előkészítéséhez.

## A Folyamat Lépései

1. **Szortírozás (`sort_by_date.py`):** A nyers képek dátum szerinti rendezése `Év/Hónap` mappákba.
2. **Előkészítés (`prepare_photos.py`):** A szortírozott képek nevének tisztítása és optimalizálása a feltöltéshez.

Ez a Python script segít a fényképek előkészítésében a Backblaze B2 (vagy bármely más felhő alapú tárhely) feltöltéséhez, ahol a speciális karakterek és a komplex mappaszerkezet akadályt jelenthetnek.

A [fénykép előkészítés](https://github.com/upstage/ "Hol tárolom a különbözző fázisokban a fényképeket") folyamata ezen a linken tekinthető át 

## 1. Szortírozás dátum szerint (`sort_by_date.py`)

Ez a script a képek metaadataiban (EXIF) tárolt készítési idő alapján rendezi a fájlokat.

### Funkciók
- **Automatikus szortírozás:** A képeket a `c:\Users\zsolt.tuske\Pictures\Véglegesített képek\[Év]\[Hónap]\` mappába mozgatja.
- **EXIF támogatás:** Elsősorban a készítés idejét nézi, ha az hiányzik, a fájl módosítási dátumát használja.
- **Mappakezelés:** Automatikusan létrehozza a szükséges év és hónap mappákat.

### Futtatás
```cmd
python sort_by_date.py "C:\FORRÁS_MAPPA"
```

## 2. Előkészítés feltöltéshez (`prepare_photos.py`)

Ez a script segít a fényképek nevének és struktúrájának tisztításában a Backblaze B2 feltöltés előtt.

### Funkciók
- **Automatikus Karaktertisztítás:** Eltávolítja az ékezeteket, a szóközöket és speciális karaktereket kötőjelre cseréli.
- **Mappaszerkezet Megőrzése:** A script megőrzi az eredeti könyvtárfát, de tisztított nevekkel hozza létre egy új mappában (`elokeszitett_kepek`).
- **Szerkesztett Képek Prioritása:** Ha egy mappában megtalálható egy kép eredeti és `-szerkesztve` végződésű változata is, csak a szerkesztett változatot dolgozza fel.
- **HEIC Konvertálás:** A HEIC/HEIF formátumú képeket automatikusan JPG-be konvertálja.

### Futtatás
1. Nyiss egy cmd ablakot a feldolgozandó képek mappájában.
2. Futtasd a `python prepare_photos.py` parancsot.
3. A tisztított képek az `elokeszitett_kepek` mappába kerülnek.

## Feltöltés a Backblaze B2-re

Mivel a böngészős feltöltés sok fájl esetén gyakran megszakad, javasoljuk a következő módszereket:

### A) B2 Parancssori Eszköz (CLI) - Javasolt

Ez a legbiztosabb módszer. Ha megszakad a kapcsolat, csak futtasd újra, és ott folytatja, ahol abbahagyta.

1. Telepítsd: `pip install b2`
2. Jelentkezz be: `b2 account authorize <keyId> <applicationKey>`
3. Szinkronizálj az alábbi módszerek egyikével:
   - **Teljes tartalom (Lépj be a mappába):**
     
     ```cmd
     cd elokeszitett_kepek
     b2 sync . b2://vödör-neve
     ```
     
     *(A `.` az aktuális mappát jelöli)*
   - **Teljes tartalom (Maradj az eredeti mappában):**
     
     ```cmd
     b2 sync elokeszitett_kepek b2://vödör-neve
     ```
   - **Csak egy adott almappa (pl. 2026/03) szinkronizálása:**
     Lépj be az `elokeszitett_kepek` mappába, majd add meg a kívánt almappát mind a forrásnál, mind a célnál:
     
     ```cmd
     cd elokeszitett_kepek
     b2 sync 2026/03 b2://vödör-neve/2026/03
     ```

### B) Cyberduck (Grafikus felület)

Ingyenes, grafikus fájlkezelő program.

1. Töltsd le: [cyberduck.io](https://cyberduck.io/)
2. Kapcsolódásnál válaszd a **Backblaze B2**-t.
3. Add meg a kulcsaidat és húzd be a fájlokat.

## Technikai részletek

...

A script a következő alapvető Python könyvtárakat használja:

- `os`, `shutil`: Fájlrendszer műveletek.
- `unicodedata`: Ékezet-mentesítés.
- `re`: Reguláris kifejezések a névtisztításhoz.

---

# Photo Management Tools (v1.2) - English

This repository contains two main scripts for organizing and preparing photos for Backblaze B2 upload.

## 1. Sort by Date (`sort_by_date.py`)
Moves photos to a structured `Year/Month` directory based on EXIF metadata.

## 2. Prepare for Upload (`prepare_photos.py`)
Cleans filenames (removes accents/spaces) and prepares the directory structure for cloud storage.

## Features

- **Character Normalization:** Removes accents and replaces special characters/spaces with dashes.
- **Path Flattening:** Includes the full relative path in the filename (e.g., `2023/Summer/img.jpg` -> `2023-summer--img.jpg`).
- **Edited Version Priority:** Automatically skips original files if a version ending in `-szerkesztve` exists.
- **Safe Copying:** Uses `shutil.copy2` to preserve metadata and keep original files intact.
- **Skip Existing Files:** Skips files that have already been processed in the root directory.

## Requirements

- Python 3.x
- No external dependencies required.
