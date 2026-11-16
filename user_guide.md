# Felhasználói útmutató: Takeout → B2 fényképfeltöltés

## Mikor kell ezt használnom?

Amikor van egy le nem töltött vagy még fel nem dolgozott Google Takeout
ZIP-ed (`C:\Users\zsolt.tuske\Pictures\Takeout\...`), és a benne lévő
fényképeket fel szeretnéd tölteni a Lumina Képtár B2-tárhelyére.

**Nem kell** semmit kicsomagolnod, mappákba rendezned vagy máshova
másolnod előtte — az eszköz közvetlenül a ZIP-ből dolgozik.

## Lépésről lépésre

### 1. Próbafuttatás (`--dry-run`)

Mindig **ezzel kezdd**, hogy lásd, mi történne, mielőtt ténylegesen
bármi feltöltődne:

```cmd
cd "M:\My Drive\IT\Programok\Képnézegető\Fénykép előkészítés BlackBlaze-be másolás"
python takeout_to_b2_feltoltes.py "C:\Users\zsolt.tuske\Pictures\Takeout\2017\takeout-....zip" --dry-run
```

A `MASOLD_BE_POWERSHELLBE_teszt.txt` fájlban van egy PowerShell-be
másolható, kész parancssor is (automatikusan megkeresi a ZIP-et, és
helyesen kódolt naplófájlba menti az eredményt).

### 2. Az eredmény átnézése

A futás után keletkezik egy napló a projekt gyökerében: próbafutásnál
`feltoltes_terv_<zip neve>_proba.csv`, éles futásnál
`feltoltes_terv_<zip neve>.csv`. A kettő külön fájl, így egy későbbi
próbafutás nem írja felül az éles feltöltés naplóját. Oszlopai:

| Oszlop | Jelentése |
|---|---|
| `takeout_utvonal` | a fájl eredeti helye a ZIP-ben |
| `sha1` | a kép tartalmának ujjlenyomata |
| `statusz` | `mar-fent-van` / `feltoltesre-kerulne` (élesben: `feltoltve` / `feltoltesi-hiba`) |
| `cel_utvonal` | a kiszámolt B2-beli célútvonal (üres, ha már fent van) |

Érdemes átfutni: ésszerű-e a `mar-fent-van` / `feltoltesre-kerulne` arány,
és néhány `cel_utvonal`-t szúrópróbaszerűen ellenőrizni (helyes év/hónap,
értelmes album-alkönyvtár-e, ha volt névvel ellátott album).

### 3. Éles feltöltés

Ha a próbafuttatás eredménye rendben van, futtasd `--dry-run` nélkül:

```cmd
python takeout_to_b2_feltoltes.py "C:\Users\zsolt.tuske\Pictures\Takeout\2017\takeout-....zip"
```

Ez ténylegesen feltölti a `feltoltesre-kerulne` státuszú képeket (és a
hozzájuk tartozó bélyegképeket) a B2-re.

### 3/b. Hibás feltöltések újrapróbálása

Ha éles feltöltés után maradt `feltoltesi-hiba` státuszú fájl, a grafikus
felületen (`Takeout_B2_Feltolto_Inditasa.bat`) aktívvá válik a
**„Hibás fájlok újrapróbálása (N db)”** gomb. Ez csak ezeket a fájlokat
tölti fel újra, ugyanarra a célútvonalra. Nem kéri le újra a B2-listát, és
nem nézi át újra a teljes ZIP-et, ezért gyors. A sikeres sorok a naplóban
`feltoltve` státuszra váltanak. A gomb addig nyomható, amíg el nem fogynak
a hibák.

A gomb akkor is aktív, ha egy **korábban már feltöltött ZIP-et választasz
ki**, és annak naplójában maradt hibás fájl. Ilyenkor az állapotsor kiírja:
„Korábbi napló: N fájl feltöltése nem sikerült - újrapróbálható.” Így nem
kell újra lefuttatni a teljes feltöltést.

Parancssorból ugyanez:

```cmd
python takeout_to_b2_feltoltes.py "C:\...\takeout-....zip" --retry-failed
```

### 3/c. A Lumina Képtár automatikus frissítése

Ha egy éles feltöltés vagy újrapróbálás során legalább 1 kép felment, a
program a végén automatikusan elindítja a Lumina Képtárban (tablet,
`http://192.168.1.157:8000`) a Kepek02 index frissítését. Ez ugyanaz,
mint a Connect menüben a Resync gomb. Indítás előtt kb. 30 mp-et vár, hogy
a B2 már biztosan listázza az új fájlokat. A frissítés állapota a Connect
menüben követhető.

* Kikapcsolható a GUI-ban: „Feltöltés után a Lumina Kepek02 index
  frissítése” jelölőnégyzet (a program gépenként megjegyzi).
* Parancssorból: `--no-lumina-sync` kapcsolóval nem indítja el.
* Ha a tablet nem érhető el, csak figyelmeztetést ír; ilyenkor a Connect
  menü Resync gombjával később kézzel indítható.

### 3/d. Feltöltési nyilvántartás: melyik ZIP-pel mi történt már?

Minden futás (próba, éles, újrapróbálás) a végén egy sort fűz a
`feltoltesi_nyilvantartas.csv` fájlhoz. Ez a fájl soha nem íródik felül,
csak bővül, és a Google Drive-on van, így minden gépről ugyanaz látszik.
Excelben is megnyitható. Egy sorban: időpont, gép, programverzió, ZIP neve,
útvonala és mérete, mód (`eles` / `proba` / `ujraproba`), a darabszámok
(egyedi, már fent, lomtárban, szándékosan törölt, feltöltésre szánt,
sikeres, hibás) és a hozzá tartozó napló neve.

A GUI-ban:

* **ZIP kiválasztásakor** az állapotsor kiírja, mi szerepel róla a
  nyilvántartásban, pl. „Élesben feltöltve: 2026-11-16 22:14 (…) - 429
  sikeres, 0 hiba.” vagy „Eddig csak próbafutás volt: …”, vagy hogy még
  nem szerepel.
* **Ha egy már élesben feltöltött ZIP-et újra élesben indítasz**, a program
  megerősítést kér. (Duplikátum ilyenkor sem kerül fel, de az előző éles
  napló felülíródik.)
* A ZIP-et a **neve és mérete** azonosítja; ha átnevezed, új ZIP-nek számít.

A nyilvántartás bevezetése (V1.7) előtti futásokat a
`nyilvantartas_potlas.py` vette fel a meglévő naplókból (gép: „ismeretlen
(pótolva)”). Újra futtatva csak azt a ZIP-et veszi fel, ami még nem szerepel:

```cmd
python nyilvantartas_potlas.py           (csak kiírja, mit venne fel)
python nyilvantartas_potlas.py --iras    (be is írja)
```

### 4. Ellenőrzés

A Lumina Képtár Dashboardján, vagy közvetlenül `rclone lsf
b2_storage:Kepek02` paranccsal nézhető meg, hogy a képek valóban
felkerültek-e.

## Mit nem kell külön kezelned

* **Már fent lévő képek**: a script a B2 teljes SHA1-listáját ellenőrzi
  induláskor — ha egy kép tartalma bárhol már megvan a vödörben (akárcsak
  más néven/mappában), nem tölti fel újra.
* **Szándékosan törölt képek**: ha egy képet korábban véglegesen
  kiürítettél a Lumina Képtár Lomtárából, annak SHA1-je bekerül a
  `deleted_sha1_list.csv`-be (a Lumina Képtár írja automatikusan) — az
  ilyen képeket a feltöltő szintén kihagyja, akkor is, ha egy Takeout
  ZIP-ben újra megtalálhatók.

## Ha több ZIP-en is végig kell menni

A `tasks.md`-ben van egy prioritási sorrend a még hiányzó tartalmú
ZIP-ekhez — egyelőre egyenként, kézzel futtatva érdemes végigmenni
rajtuk (ugyanezzel a két lépéssel: `--dry-run`, majd éles futtatás).
