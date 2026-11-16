# Takeout → B2 fényképfeltöltő eszköz

Ez a projekt egyetlen célt szolgál: a Google Takeout exportokban (ZIP-ekben)
található fényképeket **közvetlenül**, helyi köztes mappa nélkül feltölti a
Backblaze B2 felhőtárhelyre (`Kepek02` vödör), a Lumina Képtár által elvárt
mappastruktúrába rendezve.

## 0. Előfeltételek

* **Python 3.x** telepítése.
* **Szükséges könyvtárak:** `pip install Pillow pillow-heif`.
* **Rclone:** telepítve és konfigurálva `b2_storage` néven a Backblaze B2-höz.
  A remote neve minden gépen ugyanaz legyen; az rclone-konfiguráció gépenként
  külön van (titkos kulcsokat tartalmaz, ne kerüljön a Drive-ra).

### Új gép beállítása (egyszeri)

1. Python telepítése, majd a `Takeout_B2_Telepites.bat` futtatása (Pillow, pillow-heif).
2. rclone telepítése, `rclone config`: Backblaze B2, név: `b2_storage`.
3. `Takeout_B2_Feltolto_Inditasa.bat` indítása. A program induláskor
   ellenőrzi a környezetet, és magyarul kiírja, ha valami hiányzik.

### Takeout ZIP-ek helye

A ZIP-ek a NAS-on vannak: `X:\Pictures\takeout\<év>\`. A fájlválasztó az
utoljára használt mappában nyílik meg (gépenként tárolva), ennek hiányában
az `X:\Pictures\takeout\` mappában. Bármilyen más útvonalról is választható ZIP.

---

## 1. Fő eszköz: `takeout_to_b2_feltoltes.py`

```cmd
python takeout_to_b2_feltoltes.py "C:\utvonal\takeout-....zip" --dry-run
```

A `--dry-run` kapcsoló nélkül ténylegesen feltölt; azzal csak kiírja, mit
tenne.

### Mit csinál pontosan

1. Lekéri a **`Kepek02` vödör teljes SHA1-listáját** — minden kép, ami
   *tartalmilag* már fent van (bárhol a vödörben, függetlenül a fájlnévtől
   vagy mappától), **kimarad** a feltöltésből.
2. Beolvassa a **szándékosan törölt képek listáját**
   (`../deleted_sha1_list.csv`, a Lumina Képtár fő projekt gyökerében) — ezt
   a fájlt a Lumina Képtár Lomtár-funkciója írja automatikusan, amikor
   véglegesen kiürítesz egy képet. Az itt szereplő SHA1-ek **szintén
   kimaradnak** a feltöltésből, hogy a tudatosan törölt képek ne
   kerüljenek vissza.
3. A ZIP fennmaradó tartalmát a `mappazasi_algoritmus_specifikacio.md`-ben
   rögzített, EXIF-dátum és album-név alapú algoritmus szerint képezi le a
   B2-beli célútvonalra.
4. A megfelelő fájlokat és a hozzájuk generált 400px-es bélyegképeket
   **közvetlenül a ZIP-ből olvasva, helyi ideiglenes fájl nélkül**
   streameli fel (`rclone rcat`) a `Kepek02` és `kepek02-thumbs`
   vödrökbe.
5. A futás végén egy `feltoltes_terv_<zip neve>.csv` naplót ír a projekt
   gyökerébe (fájlonként: forrás útvonal, SHA1, státusz, célútvonal).

### Mit NEM csinál

* Nincs helyi "Véglegesített képek" köztes mappa — a régi munkafolyamat
  ezen lépése megszűnt.
* Videókat nem tölt fel (a Lumina Képtár jelenleg nem kezeli őket).

---

## 2. Kapcsolódó dokumentáció

* [`mappazasi_algoritmus_specifikacio.md`](./mappazasi_algoritmus_specifikacio.md) —
  a célútvonal-számítás pontos szabályai.
* [`tasks.md`](./tasks.md) — fejlesztési feladatlista és állapot.
* [`Implementation_plan.md`](./Implementation_plan.md) — a jóváhagyott terv.
* [`verziokontroll.md`](./verziokontroll.md) — verzió- és commit-történet.
* [`user_guide.md`](./user_guide.md) — lépésről lépésre útmutató a
  tényleges használathoz.

---

## 3. Egyéb, még használt segédeszközök

Ezek nem a Takeout-feltöltés részei, de önállóan még hasznosak:

* **`sort_by_date.py`** — nem Takeout-forrású (pl. más géppel készült)
  helyi képek rendezése Év/Hónap (és album-név, ha van) mappastruktúrába,
  ugyanazzal az algoritmussal, mint a fő eszköz. `--dry-run` móddal
  tesztelhető.
* **`manage_thumbnails.py`** — felhő-alapú karbantartó: ha a B2-n hiányzik
  egy bélyegkép, letölti az eredetit, legenerálja, és visszatölti.
* **`set_b2_lifecycle.py`** — B2 vödrök verziókezelési/életciklus
  szabályainak beállítása (a benne szereplő vödörlista felülvizsgálatra
  szorulhat, több benne lévő név már nem aktív).

## 4. Elemző/egyeztető eszközök

A [`Takout-B2 könyvtár átalakítás/`](./Takout-B2%20könyvtár%20átalakítás/)
mappában találhatók a teljes Takeout-állomány és a B2-tartalom
összevetésére/az algoritmus empirikus ellenőrzésére használt scriptek
(`takeout_b2_teljes_egyeztetes.py`, `album_hipotezis_ellenorzes.py`) és
a belőlük generált (git által figyelmen kívül hagyott) riportfájlok.
