# Backblaze B2 Photo Preparation Script (v1.1)

Ez a Python script segít a fényképek előkészítésében a Backblaze B2 (vagy bármely más felhő alapú tárhely) feltöltéséhez, ahol a speciális karakterek és a komplex mappaszerkezet akadályt jelenthetnek.

## Funkciók

- **Automatikus Karaktertisztítás:** Eltávolítja az ékezeteket, a szóközöket és speciális karaktereket kötőjelre cseréli a fájl- és mappanevekben is.
- **Mappaszerkezet Megőrzése:** A script megőrzi az eredeti könyvtárfát (pl. `2023/Nyar/Balaton`), de tisztított nevekkel hozza létre egy új mappában (`elokeszitett_kepek`).
- **Kizárólag Képek:** Csak a támogatott képfájlokat (`.jpg`, `.png`, `.cr2`, `.nef`, stb.) másolja, a szemetet kiszűri.
- **Szerkesztett Képek Prioritása:** Ha egy mappában megtalálható egy kép eredeti és `-szerkesztve` végződésű változata is, a script csak a szerkesztett változatot dolgozza fel.
- **Biztonságos Másolás:** Nem töröl semmit, az összes feldolgozott képet az `elokeszitett_kepek` mappába gyűjti.

## Futtatás: fényképek előkészítése
1. Nyiss egy cmd ablakot
2. Menj abba a mappába, amely alatt az átalakítandó fényképek vannak
3. Másold ebbe a mappába a prepare_photos.py file-t
4. Futtasd a python prepare_photos.py parancsot
5. 

## Feltöltés a Backblaze B2-re

Mivel a böngészős feltöltés sok fájl esetén gyakran megszakad, javasoljuk a következő módszereket:

### A) B2 Parancssori Eszköz (CLI) - Javasolt
Ez a legbiztosabb módszer. Ha megszakad a kapcsolat, csak futtasd újra, és ott folytatja, ahol abbahagyta.

1. Telepítsd: `pip install b2`
2. Jelentkezz be: `b2 account authorize <keyId> <applicationKey>`
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
