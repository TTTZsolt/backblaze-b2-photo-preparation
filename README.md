# Backblaze B2 Photo Preparation Script (v1.0.0)

Ez a Python script segít a fényképek előkészítésében a Backblaze B2 (vagy bármely más felhő alapú tárhely) feltöltéséhez, ahol a speciális karakterek és a komplex mappaszerkezet akadályt jelenthetnek.

## Funkciók

- **Automatikus Karaktertisztítás:** Eltávolítja az ékezeteket, a szóközöket és speciális karaktereket kötőjelre cseréli.
- **Mappaszerkezet Lapítása:** A teljes relatív útvonalat beépíti a fájlnévbe (pl. `2023/Nyar/kep.jpg` -> `2023-nyar--kep.jpg`), és a fájlokat a főkönyvtárba másolja.
- **Szerkesztett Képek Prioritása:** Ha egy mappában megtalálható egy kép eredeti és `-szerkesztve` végződésű változata is, a script csak a szerkesztett változatot dolgozza fel.
- **Biztonságos Másolás:** Nem törli az eredeti fájlokat, csak másolatokat készít.
- **Idempotens működés:** Ha újra lefuttatod, a már létező célfájlokat átugorja.

## Használat

1. Telepítsd a Pythont (ha még nincs fent).
2. Másold a `prepare_photos.py` fájlt abba a mappába, ahol a fotóid vannak.
3. Nyiss egy terminált / parancssort ebben a mappában.
4. Futtasd a scriptet:
   ```bash
   python prepare_photos.py
   ```

## Technikai részletek

A script a következő alapvető Python könyvtárakat használja:
- `os`, `shutil`: Fájlrendszer műveletek.
- `unicodedata`: Ékezet-mentesítés.
- `re`: Reguláris kifejezések a névtisztításhoz.

---

# Backblaze B2 Photo Preparation Script (v1.0.0) - English

This Python script helps prepare photos for Backblaze B2 upload by cleaning filenames and flattening directory structures.

## Features

- **Character Normalization:** Removes accents and replaces special characters/spaces with dashes.
- **Path Flattening:** Includes the full relative path in the filename (e.g., `2023/Summer/img.jpg` -> `2023-summer--img.jpg`).
- **Edited Version Priority:** Automatically skips original files if a version ending in `-szerkesztve` exists.
- **Safe Copying:** Uses `shutil.copy2` to preserve metadata and keep original files intact.
- **Skip Existing Files:** Skips files that have already been processed in the root directory.

## Requirements

- Python 3.x
- No external dependencies required.
