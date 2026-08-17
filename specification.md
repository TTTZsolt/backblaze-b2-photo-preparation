# Projekt Specifikáció: Fénykép előkészítés és B2 feltöltés

## Cél
A projekt célja egy olyan moduláris Python alapú rendszer biztosítása, amely automatizálja a nyers fényképek válogatását, dátum alapú szortírozását, technikai előkészítését (ékezetmentesítés, HEIC konverzió, bélyegkép-generálás) és a Backblaze B2 felhőtárhelyre történő biztonságos feltöltését és szinkronizációs ellenőrzését.

## Elvárások és Funkciók

1. **Fájlok Tisztítása és Formázása**:
   - A rendszernek automatikusan el kell távolítania az ékezeteket és szóközöket a fájlnevekből és a mappanevekből a felhőbeli kompatibilitás miatt.
   - HEIC formátumú iOS képek automatikus konvertálása standard JPEG formátumra.

2. **Képek Intelligens Előkészítése (`prepare_photos.py`)**:
   - Ha egy képnek létezik szerkesztett változata (pl. tartalmazza a `-szerkesztett` vagy `-edit` szót a névben), a programnak ki kell hagynia az eredeti verzió feltöltését a duplikáció elkerülésére.
   - Minden felbontású képhez automatikusan le kell generálni egy 400px széles JPEG bélyegképet (thumbnail) a gyors diavetítéses előnézetekhez.

3. **Backblaze B2 Szinkronizáció**:
   - Az eredeti képek feltöltése a `Kepek02` vödörbe, míg a generált bélyegképek feltöltése a `kepek02-thumbs` vödörbe történik.
   - Rclone (`b2_storage` profilon keresztüli) integráció a fájlok gyors és stabil másolásához.
   - Feltöltési darabszámok és integritás automatikus ellenőrzése (`check_sync.py`).

4. **Karbantartási segédeszközök**:
   - Duplikációk utólagos tisztítása (`cleanup_duplicates.py`).
   - Bélyegképek felhő-szintű karbantartása (`manage_thumbnails.py`) – ha a felhőben hiányzik egy thumbnail, a program letölti az eredetit, legenerálja a kicsit, és visszatölti.
   - A B2 fájl-életciklusok és verziók konfigurálása a felhőben (`set_b2_lifecycle.py`).
