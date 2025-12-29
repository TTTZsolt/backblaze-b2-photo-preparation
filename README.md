# Backblaze B2 Photo Preparation Script (v1.0.0)

Ez a Python script segít a fényképek előkészítésében a Backblaze B2 (vagy bármely más felhő alapú tárhely) feltöltéséhez, ahol a speciális karakterek és a komplex mappaszerkezet akadályt jelenthetnek.

## Funkciók

- **Automatikus Karaktertisztítás:** Eltávolítja az ékezeteket, a szóközöket és speciális karaktereket kötőjelre cseréli.
- **Mappaszerkezet Lapítása:** A teljes relatív útvonalat beépíti a fájlnévbe (pl. `2023/Nyar/kep.jpg` -> `2023-nyar--kep.jpg`), és a fájlokat a főkönyvtárba másolja.
- **Szerkesztett Képek Prioritása:** Ha egy mappában megtalálható egy kép eredeti és `-szerkesztve` végződésű változata is, a script csak a szerkesztett változatot dolgozza fel.
- **Biztonságos Másolás:** Nem törli az eredeti fájlokat, csak másolatokat készít.
- **Idempotens működés:** Ha újra lefuttatod, a már létező célfájlokat átugorja.

## Feltöltés a Backblaze B2-re

Mivel a böngészős feltöltés sok fájl esetén gyakran megszakad, javasoljuk a következő módszereket:

### A) B2 Parancssori Eszköz (CLI) - Javasolt
Ez a legbiztosabb módszer. Ha megszakad a kapcsolat, csak futtasd újra, és ott folytatja, ahol abbahagyta.

1. Telepítsd: `pip install b2`
2. Jelentkezz be: `b2 authorize-account <keyId> <applicationKey>`
3. Szinkronizálj: `b2 sync . b2://vödör-neve`

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
