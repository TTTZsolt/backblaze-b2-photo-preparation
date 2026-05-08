# Fénykép Kezelő és B2 Feltöltő Rendszer (v1.4)

Ez a projekt a fényképek rendszerezését, válogatását, technikai előkészítését (tisztítás, konvertálás) és a Backblaze B2 felhőtárhelyre való automatizált feltöltését és ellenőrzését valósítja meg.

## 0. Előfeltételek (Requirements)

A rendszer futtatásához a következőkre van szükség:
*   **Python 3.x** telepítése.
*   **Szükséges könyvtárak:** `pip install Pillow pillow-heif`.
*   **Rclone:** Telepítve és konfigurálva a `b2_storage` néven a Backblaze B2-höz.

---

## 1. A Teljes Munkafolyamat (Workflow)

A képek útja a fényképezőgéptől a felhőig:

1.  **Válogatás (`valogato.py`):** A nyers képek közül a megtartandók kiválogatása.
2.  **Szortírozás (`sort_by_date.py`):** A válogatott képek Év/Hónap szerinti mappákba rendezése.
3.  **Előkészítés és Feltöltés (`prepare_photos.py`):**
    *   Fájlnevek tisztítása (ékezetek és szóközök eltávolítása).
    *   Szerkesztett változatok keresése (eredeti kihagyása).
    *   HEIC konvertálás és 400px-es bélyegképek (thumbnails) generálása.
    *   Automatikus feltöltés a B2 `Kepek02` és `kepek02-thumbs` vödrökbe.
4.  **Ellenőrzés (`check_sync.py`):** A helyi és a felhőbeli fájlok darabszámának összevetése.

---

## 2. Használati Útmutató (Parancsok)

### A. Válogatás (Opcionális)
Ha gyorsan szeretnéd kiválogatni a képeket:
```cmd
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\valogato.py"
```
*Irányítás:* **[Jobbra nyíl]** = Megtart, **[Balra nyíl]** = Kihagy, **[Z]** = Vissza.

### B. Szortírozás
Rendezd a képeket év/hónap bontásba:
```cmd
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\sort_by_date.py" "C:\FORRÁS_MAPPA"
```

### C. Előkészítés és Feltöltés
Ez a legfontosabb lépés, a véglegesített képek mappájában kell futtatni:
```cmd
cd "c:\Users\zsolt.tuske\Pictures\Véglegesített képek"
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\prepare_photos.py"
```

### D. Szinkronizáció Ellenőrzése
```cmd
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\check_sync.py"
```

---

## 3. Karbantartó és Speciális Eszközök

### Duplikációk Takarítása (`cleanup_duplicates.py`)
Eltávolítja azokat az eredeti képeket, amiknek már van szerkesztett változata:
```cmd
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\cleanup_duplicates.py"
```

### Bélyegkép Karbantartó (`manage_thumbnails.py`)
Teljesen felhő-alapú eszköz. Ha hiányzik egy bélyegkép a B2-n, letölti a nagy képet, legenerálja és visszatölti a kicsit:
```cmd
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\manage_thumbnails.py"
```

### Logok Feldolgozása (`process_logs.py`)
Az rclone feltöltési naplójából készít `processed_logs.csv` fájlt a Google Sheets-be való importhoz:
```cmd
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\process_logs.py"
```

### B2 Életciklus beállítása (`set_b2_lifecycle.py`)
Beállítja a vödrökhöz az optimális verziókezelési szabályokat:
```cmd
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\set_b2_lifecycle.py"
```

---

## 4. Technikai részletek
*   **Ékezetmentesítés:** A rendszer minden fájlnevet és mappanevet automatikusan tisztít a B2 kompatibilitás miatt.
*   **Intelligens Skip:** A `prepare_photos.py` nem dolgozza fel újra, ami már megvan (kivéve ha a thumbnail hiányzik).
*   **Idempotencia:** Minden eszköz többször is futtatható, nem okoznak kárt vagy felesleges duplikációt.

---
*Utolsó frissítés: 2026.05.08 (v1.4)*
