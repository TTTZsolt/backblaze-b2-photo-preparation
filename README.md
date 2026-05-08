# Fénykép Kezelő és B2 Feltöltő Rendszer (v1.2)

Ez a projekt a fényképek rendszerezését, előkészítését és a Backblaze B2 felhőtárhelyre való automatizált feltöltését valósítja meg.

## 1. A Teljes Munkafolyamat (Workflow)

A rendszer három fő fázison viszi keresztül a képeket:

### A. Rendszerezés (`sort_by_date.py`)
*   **Forrás:** Bármilyen mappa, ahol az új, ömlesztett képek vannak.
*   **Cél:** `c:\Users\zsolt.tuske\Pictures\Véglegesített képek\[ÉV]\[HÓNAP]\`
*   **Művelet:** A képeket az EXIF (készítési dátum) adatok alapján év/hónap bontású mappákba mozgatja.

### B. Előkészítés és Tisztítás (`prepare_photos.py`)
*   **Futtatási hely:** `c:\Users\zsolt.tuske\Pictures\Véglegesített képek\`
*   **Kimeneti mappák (automatikusan létrejönnek):**
    *   `.\elokeszitett_kepek\` -> Tisztított nevű nagy képek.
    *   `.\elokeszitett_thumbnails\` -> 400px-es bélyegképek a vetítéshez.
*   **Háttérfolyamatok:**
    1.  **Névtisztítás:** Ékezetek eltávolítása, szóközök/speciális karakterek cseréje kötőjelre (B2 kompatibilitás).
    2.  **Szerkesztett képek kezelése:** Ha létezik `-szerkesztve` végű fájl, az eredetit kihagyja.
    3.  **HEIC Konvertálás:** Az iPhone formátumú képeket automatikusan JPG-be alakítja.
    4.  **Bélyegkép generálás:** Minden új képhez készít egy 400px széles JPEG előnézetet.

### C. Automatikus Feltöltés (Rclone integráció)
A `prepare_photos.py` végén automatikusan elindul a feltöltés a Backblaze B2-re:
*   `elokeszitett_kepek` -> `b2://Kepek02` vödörbe.
*   `elokeszitett_thumbnails` -> `b2://kepek02-thumbs` vödörbe.

---

## 2. Használati Útmutató (Parancsok)

### 1. Lépés: Szortírozás
Ha új képeid vannak (pl. egy pendrive-on vagy letöltve), rendezd őket a végleges helyükre:
```cmd
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\sort_by_date.py" "C:\FORRÁS_MAPPA"
```

### 2. Lépés: Előkészítés és Feltöltés
Lépj be a véglegesített képek mappájába, és futtasd az előkészítőt:
```cmd
cd "c:\Users\zsolt.tuske\Pictures\Véglegesített képek"
python "m:\Saját meghajtó\IT\Programok\Fénykép előkészítés BlackBlaze-be másolás\prepare_photos.py"
```

---

## 3. Hogyan kerüljük el a duplikációkat?

A rendszer három szinten védekezik a többszörös feltöltés és a felesleges adattárolás ellen:

1.  **Helyi ellenőrzés (`prepare_photos.py`):**
    A script ellenőrzi az `elokeszitett_kepek` mappát. Ha egy fájl már létezik ott tisztított névvel, **átugorja a feldolgozást** (nem generálja újra a thumbnail-t sem).
    
2.  **Intelligens szinkronizáció (`rclone`):**
    A feltöltés az `--update` kapcsolóval fut. Ez azt jelenti, hogy az `rclone` csak akkor tölt fel egy fájlt, ha az **még nincs fenn** a B2-n, vagy ha a helyi változat **újsabb/nagyobb**, mint a felhőbeli.

3.  **Felhő oldali verziókezelés (B2 Lifecycle):**
    Beállítottunk egy életciklus szabályt ("Keep only last version"), ami biztosítja, hogy ha egy képet (vagy annak metaadatait) frissítjük, a Backblaze B2 automatikusan törölje a régi verziókat 1 nap után, így nem foglalják a helyet.

---

## 4. Karbantartó Eszközök

### B2 Életciklus beállítása (`set_b2_lifecycle.py`)
Ha új vödröt hozol létre, ezzel a scripttel tudod egy lépésben beállítani rajta az optimális verziókezelési szabályokat:
```cmd
python set_b2_lifecycle.py
```

### Kézi szinkronizáció (ha szükséges)
Ha csak a feltöltést szeretnéd újrafuttatni az előkészítés nélkül:
```cmd
rclone copy "c:\...\elokeszitett_kepek" b2_storage:Kepek02 -P --update
```

---
*Utolsó frissítés: 2026.05.08 (v1.2)*
