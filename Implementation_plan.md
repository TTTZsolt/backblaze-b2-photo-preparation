# Implementation_plan.md — Közvetlen Takeout → B2 feltöltés

Kapcsolódó dokumentumok: [mappazasi_algoritmus_specifikacio.md](./mappazasi_algoritmus_specifikacio.md),
[tasks.md](./tasks.md)

## Előzmény / motiváció

A Lenovo-ról 2026-08-15-én feltöltött Google Photos Takeout képek egy
egyeztetése (`Takout-B2 könyvtár átalakítás/`) kimutatta, hogy kb. 4 362
kép hiányzik a B2 `Kepek02` vödörből. A hiányzók pótlásához, és a jövőbeli
Takeout-feltöltésekhez, a régi kétlépcsős munkafolyamat
(`sort_by_date.py` → helyi "Véglegesített képek" mappa → `prepare_photos.py`
→ `rclone` feltöltés) helyett/mellett egy **közvetlen, egylépéses** eszközt
kértél: Takeout ZIP → B2, köztes helyi fájl nélkül.

## Cél

Egy script (`takeout_to_b2_feltoltes.py`), ami:
1. Bemenetként egyetlen Takeout ZIP fájl útvonalát kapja.
2. A `mappazasi_algoritmus_specifikacio.md`-ben rögzített (empirikusan
   30,4%-os igazolt találati arányú) album-név alapú algoritmussal számolja
   ki minden kép B2-célútvonalát.
3. A ZIP-ből kiolvasott bájtokat **közvetlenül** (helyi ideiglenes fájl
   nélkül, `rclone rcat` streameléssel) tölti fel a B2-re.
4. Feltöltés előtt lekéri a B2-n már meglévő tartalom SHA1-listáját, és
   **kihagyja azt, ami tartalmilag már fent van** — nem tölt fel duplikátumot.
5. Támogat egy `--dry-run` módot: csak kiírja/naplózza a tervezett
   műveleteket, ténylegesen nem tölt fel semmit — ezt kell **először**
   használni minden új ZIP-nél, éles feltöltés előtt.

## Jóváhagyott terv (2026-08-16)

A tervet a chat-ben egyeztettük és jóváhagytad, mielőtt a kód megíródott:
- Nincs helyi köztes fájl/mappa, minden memóriában történik.
- Kétmenetes feldolgozás ZIP-en belül: 1) SHA1 alapú tartalom-indexelés,
  hogy felismerje, egy kép szerepel-e nevesített albumban is; 2) célútvonal-
  számítás + feltöltés csak azokra, amik még nincsenek fent.
- HEIC→JPG konverzió és 400px thumbnail-generálás feltöltés előtt, a
  meglévő `prepare_photos.py` logikájával megegyezően.
- Videó továbbra sem kerül feltöltésre.
- `--dry-run` biztonsági mód, mert ez a script **közvetlenül az éles**
  `Kepek02` vödörbe töltene fel.

## Állapot: **tesztelésre vár, még nem futott le**

A script megíródott, de **még senki nem futtatta**, mert amikor kész lett,
nem voltál a Lenovo közelében (ahol a Takeout ZIP-ek helyben vannak).
Lásd a [tasks.md](./tasks.md) pontos, kipipálható lépéseit a folytatáshoz.
