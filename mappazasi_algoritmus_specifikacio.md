# B2 mappázási algoritmus specifikáció (Takeout → B2)

**Cél:** rögzíteni azt az algoritmust, amellyel egy Google Photos Takeout
exportból származó kép/videó B2-beli (`Kepek02`) célútvonala **determinisztikusan,
programozottan** meghatározható — a jövőbeli feltöltésekhez használandó
egységes szabályként.

**Eredet:** ez a szabály a 2026-08-16-i teljes körű Takeout↔B2 egyeztetés
(`Takout-B2 könyvtár átalakítás\takeout_b2_teljes_egyeztetes.csv`, 3 480
találat) empirikus elemzéséből lett levezetve. A meglévő (2011–2026 közötti)
B2-tartalom nagy része **kézzel, esetenként pontatlanul** lett rendezve, ezért
ez a szabály a találatok **30,4%-át** (1 057+269 = 1 326 / 3 480 fájl) magyarázza
meg pontosan — ez a szabály **jövőbeli, új feltöltésekre** vonatkozó előírás,
**nem** a régi tartalom visszamenőleges javítására.

---

## 1. Bemenet

Egy Takeout-fájl (kép vagy videó) az alábbi információkkal rendelkezik:

- **Fájlnév** és **kiterjesztés**.
- **EXIF `DateTimeOriginal`** (ha van) — ez az elsődleges, megbízható dátumforrás.
  Ha nincs EXIF, a fájl/ZIP-bejegyzés módosítási ideje a tartalék dátumforrás
  (ugyanúgy, mint a `sort_by_date.py`-ban).
- **Takeout-beli szülőmappa neve** — a Google Fotók export mindegyik fájlt
  elhelyezi egy általános, évenkénti gyűjtőmappában (pl. `2012 fotói` /
  `Photos from 2012`), és **emellett, párhuzamosan**, minden Google Fotók
  albumhoz tartozó másolatot egy, az album nevét viselő mappában is
  (pl. `2012_09_08 Asztalhoz emberek koncert`).

---

## 2. Algoritmus

### 2.1 Album-mappanév felismerése

A szülőmappa nevét négy mintával próbáljuk illeszteni (a dátumrészek
elválasztója lehet `_` vagy `-` is — a Google Takeout ZIP-enként eltérően
használja a kettőt):

- **Napos minta**: `ÉÉÉÉ_HH_NN Esemény neve` / `ÉÉÉÉ-HH-NN Esemény neve`
  (pl. `2012_09_08 Asztalhoz emberek koncert`, `2017-12-29 Julcsi szalagavató`)
  → kinyert mezők: album_év, album_hónap, album_nap, esemény_szöveg
- **Hónapos minta**: `ÉÉÉÉ_HH Esemény neve` / `ÉÉÉÉ-HH Esemény neve`
  (pl. `2017-06 Dűne Fro`, `2016-07 Görögország`)
  → kinyert mezők: album_év, album_hónap, esemény_szöveg (a nap az
  album-névben nincs benne, a célútvonal nap-mezője ilyen album esetén is
  mindig az EXIF-ből jön, l. 2.2)
- **Év-szintű minta**: `ÉÉÉÉ Esemény neve` (pl. `2012 Állatok`), **kivéve** ha az
  "Esemény neve" rész generikus gyűjtőmappára utaló szót tartalmaz
  (`fotói`, `photos`, `videói`, `videoi`) — ezek NEM számítanak névvel
  ellátott albumnak, hanem az általános gyűjtőmappák.
- **Dátum-előtag nélküli, szöveges minta**: a mappanév maga az esemény
  szövege, évszám-előtag nélkül (pl. `karácsony`) → kinyert mező:
  esemény_szöveg. Ilyenkor is mindig az EXIF adja az év/hónap/nap
  mezőket (l. 2.2). **Kivétel** (ezek NEM számítanak névvel ellátott
  albumnak): a puszta számjegyekből álló mappanév (pl. `2015`), és az
  `@` karaktert tartalmazó mappanév (más Google-fiókból megosztott/
  importált album jele, pl. `11Titkár, valaki@gmail.com`).

Ha egy fájlnak **több** Takeout-beli előfordulása is van (mert több albumban
is szerepel, az általános gyűjtőmappán kívül), és **legalább egyik** ilyen
névvel ellátott albumban van, akkor az albumos ágat kell használni (2.2), az
általános gyűjtőmappát figyelmen kívül kell hagyni.

### 2.2 Célútvonal képzése — VAN névvel ellátott album

```
{EXIF_év}/{EXIF_hónap:02d}/{EXIF_nap:02d}-{tisztított(esemény_szöveg)}/{tisztított(fájlnév)}{kiterjesztés}
```

Fontos: az **év/hónap/nap az EXIF-ből** jön, **nem** az album mappanevéből
beágyazott dátumból — az album-mappanév dátumrésze a gyakorlatban több
esetben pontatlannak/hibásnak bizonyult (feltehetően emberi elgépelés/
téves emlékezés az album elnevezésekor), az EXIF viszont a kamera által
rögzített, megbízható forrás. Az albumból **kizárólag az esemény-szöveg**
(a dátum-előtag utáni szabad szöveg rész) kerül felhasználásra.

Ha az EXIF hiányzik (csak tartalék dátum áll rendelkezésre), az album saját
dátummezői (album_év/hónap/nap) használandók helyette.

### 2.3 Célútvonal képzése — NINCS névvel ellátott album

Tiszta EXIF-alapú (a `sort_by_date.py` eredeti logikája):

```
{EXIF_év}/{EXIF_hónap:02d}/{tisztított(fájlnév)}{kiterjesztés}
```

### 2.4 Névtisztítás (`tisztított(...)`)

Azonos a `prepare_photos.py` `clean_string()` függvényével:
1. Unicode NFD-normalizálás, ékezet- (kombináló-) jelek eltávolítása.
2. Kisbetűsítés.
3. Minden `a-z`, `0-9`, pont karakteren kívüli karakter (szóköz, aláhúzás,
   ékezet stb.) kötőjelre cserélődik.
4. Egymást követő kötőjelek összevonása egyetlen kötőjellé.
5. Kötőjelek levágása a szöveg elejéről/végéről.

### 2.5 HEIC/HEIF és videó

- HEIC/HEIF kiterjesztés a célon mindig `.jpg`-re konvertálódik.
- Videó (`.mp4 .mov .avi .mkv .3gp .m4v .webm`) **nem kerül feltöltésre** a
  jelenlegi rendszerben (a Lumina Képtár nem kezeli a videókat) — ezt a
  szabályt a fenti algoritmus is megőrzi, videóra nem alkalmazandó.

---

## 3. Ismert korlátok

- A szabály a régi (2011–2026 közötti, jelentős részben kézzel rendezett)
  B2-tartalom **69,6%-át NEM** reprodukálja pontosan — ez a régi adatokra
  vonatkozó tény, nem a szabály hibája; a régi struktúra egy része
  visszamenőlegesen nem rekonstruálható algoritmikusan (l.
  `takeout_b2_atalakitasi_logika.md`, 4. fejezet).
- Ha egy fájl **több különböző nevű** albumban is szerepel egyszerre
  (több esemény ugyanarról a napról), az algoritmus **nem dönti el**,
  melyiket használja — ez esetben emberi döntés szükséges, vagy a fájl
  többször (több célmappában) is feltölthető.
- Az album-mappanév mintaillesztése (2.1) nem ismer fel minden lehetséges
  elnevezési konvenciót — ha a jövőben új album-elnevezési formátum
  jelenik meg, a mintákat bővíteni kell.
  - 2026-08-16: a teljes Takeout-állomány átvizsgálásával talált,
    korábban fel nem ismert mappanév-típusok — döntés született mindről:
    - dátum-előtag nélküli, tisztán szöveges albumnév (pl. `karácsony`,
      58 fájl a teszt-ZIP-ekben) — **implementálva** a fenti negyedik
      (szöveges) mintaként.
    - megosztott (más Google-fiókból importált) album mappaneve
      (`11Titkár, tuskecsaladikepek@gmail.com`, 9 fájl) — **szándékosan
      figyelmen kívül hagyva** (nem kezeljük albumként), mert a mappanév
      technikai/fiók-azonosító jellegű, nem valódi esemény-név.
    - puszta évszám, esemény-szöveg nélkül (`2015`, 1 fájl) — **szándékosan
      figyelmen kívül hagyva**, elhanyagolható méretű egyedi eset.

---

## 4. Referencia implementáció

A fenti szabály (a nap-előtaggal és esemény-névvel dolgozó változat) a
`Takout-B2 könyvtár átalakítás\album_hipotezis_ellenorzes.py` szkript
`predict_from_album()` függvényében van implementálva és tesztelve, a
`--from-cache` móddal újrafuttatható a `takeout_b2_teljes_egyeztetes.py`
mellett.
