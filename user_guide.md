# Felhasználói Útmutató: Fénykép előkészítés és B2 feltöltő rendszer

## Gyors Áttekintés
Ez a rendszer Python szkriptekből és Rclone integrációból áll, amely segít a nyers képek kiválogatásában, év/hónap szerinti rendezésében, a fájlnevek tisztításában, HEIC konverziójában, bélyegképek (thumbs) előállításában, valamint a Backblaze B2-re való biztonságos feltöltésben.

## Használati Útmutató (Lépésről lépésre)

1. **Előfeltételek**:
   - Python 3.x telepítése.
   - Pillow és pillow-heif könyvtárak telepítése:
     ```powershell
     pip install Pillow pillow-heif
     ```
   - Rclone telepítése és beállítása `b2_storage` profillal a Backblaze B2 felhőhöz.

2. **Képek Válogatása (`valogato.py`)** *(Opcionális)*:
   - Ha a nyers fotókat szeretnéd átnézni és kiválogatni:
     ```powershell
     python "m:\My Drive\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\valogato.py"
     ```
   - *Vezérlés a felugró ablakban*:
     - **[Jobbra nyíl]** = Kép megtartása (átmásolás a válogatott mappába).
     - **[Balra nyíl]** = Kép kihagyása.
     - **[Z billentyű]** = Utolsó döntés visszavonása.

3. **Mappába rendezés dátum alapján (`sort_by_date.py`)**:
   - Rendezd a válogatott képeket Év/Hónap struktúrába (pl. `2026/06_Junius/`):
     ```powershell
     python "m:\My Drive\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\sort_by_date.py" "C:\UTON_LEVO_FORRAS_MAPPA"
     ```

4. **Képek előkészítése és feltöltése (`prepare_photos.py`)**:
   - Menj a véglegesített képeid helyi mappájába:
     ```powershell
     cd "c:\Users\Zsolt\Pictures\Véglegesített képek"
     ```
   - Futtasd az előkészítő és feltöltő programot:
     ```powershell
     python "m:\My Drive\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\prepare_photos.py"
     ```
   - A script megtisztítja a neveket (ékezetmentesítés), konvertálja a HEIC fájlokat, legenerálja a 400px-es bélyegképeket a `-thumbs` mappába, és feltölti őket a B2 `Kepek02` vödrébe.

5. **Szinkronizáció Ellenőrzése (`check_sync.py`)**:
   - Ellenőrizd, hogy a helyi fájlok száma megegyezik-e a felhőbelivel:
     ```powershell
     python "m:\My Drive\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\check_sync.py"
     ```

6. **Karbantartási Parancsok**:
   - **Duplikációk törlése**: Ha egy képnek van szerkesztett változata, törli a felesleges nyerset:
     ```powershell
     python "m:\My Drive\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\cleanup_duplicates.py"
     ```
   - **Bélyegkép javítás a felhőben**: Ha a felhőben hiányzik egy bélyegkép, automatikusan pótolja:
     ```powershell
     python "m:\My Drive\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\manage_thumbnails.py"
     ```
