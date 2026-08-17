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

A futás után keletkezik egy `feltoltes_terv_<zip neve>.csv` fájl a
projekt gyökerében. Oszlopai:

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
