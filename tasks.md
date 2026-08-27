# tasks.md — Közvetlen Takeout → B2 feltöltés

Kapcsolódik: [Implementation_plan.md](./Implementation_plan.md)

## Előkészítés (kész)

- [x] Takeout↔B2 teljes körű egyeztetés elkészítése (2026-08-16) —
      `Takout-B2 könyvtár átalakítás/takeout_b2_teljes_egyeztetes.py`,
      eredmény: 3 480 találat, 4 362 hiányzó, 132 videó (szándékosan kimaradt)
- [x] A régi (kézi + script) mappázási logika dokumentálása —
      `takeout_b2_atalakitasi_logika.md`
- [x] Album-név alapú hipotézis empirikus ellenőrzése —
      `Takout-B2 könyvtár átalakítás/album_hipotezis_ellenorzes.py`,
      eredmény: 30,4%-os igazolt találati arány (1 326 / 3 480 fájl)
- [x] Végleges algoritmus-specifikáció megírása —
      `mappazasi_algoritmus_specifikacio.md`
- [x] `sort_by_date.py` átdolgozása az új algoritmus szerint (V1.5,
      `--dry-run` kapcsolóval) — **commitolva** (`8a6b599`, csak ez a 3 fájl:
      `sort_by_date.py`, `verziokontroll.md`, `mappazasi_algoritmus_specifikacio.md`)

## Közvetlen Takeout → B2 feltöltő script

- [x] Terv egyeztetve és jóváhagyva (2026-08-16, l. Implementation_plan.md)
- [x] `takeout_to_b2_feltoltes.py` megírva (közvetlen ZIP→B2 streamelés,
      SHA1-duplikátum-védelem, `--dry-run` mód)
- [x] Teszt-ZIP kiválasztva: `takeout-2017-20260331T162139Z-3-001.zip`
      (669 fájl, ebből ~12 nevesített albumban — mindkét ág tesztelhető rajta)
- [x] Másolható teszt-parancs elkészítve:
      `MASOLD_BE_POWERSHELLBE_teszt.txt`
- [x] Dry-run teszt lefuttatása a Lenovo-n (2026-08-16) — a
      `teszt_futtatas_eredmeny.txt` UTF-16 kódolással készült
      (`Tee-Object -FilePath` alapértelmezett kódolása PowerShell 5.1-ben),
      ezért olvashatatlannak tűnt. A script logikája hibátlannak
      bizonyult: a notebookon (Bash-ből) megismételt futtatás pontosan
      ugyanazt az eredményt adta (477 egyedi tartalom, 65 már fent, 412
      feltöltésre szánt), helyesen dekódolt ékezetes fájlnevekkel. A
      `MASOLD_BE_POWERSHELLBE_teszt.txt` javítva két lépésben: (1) a
      `Tee-Object` ezen a PowerShell-verzión nem támogatja az `-Encoding`
      paramétert, ezért `Out-File -FilePath ... -Encoding utf8`-ra cserélve
      (élő konzolos kiírás nélkül, csak fájlba ír); (2) ez önmagában még
      kettős kódolási hibát ("mojibake") okozott, mert a PowerShell a
      Python UTF-8 kimenetét rossz kódlapon olvasta be a csővezetéken —
      ezt a `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`
      sor hozzáadása oldotta meg a python-hívás előtt. A javított parancsot
      a Lenovo-n (HUL-0185) közvetlenül leteszteltem, a
      `teszt_futtatas_eredmeny.txt` és a
      `feltoltes_terv_takeout-2017-20260331T162139Z-3-001.csv` most már
      elejétől végéig hibátlan kódolású.
- [x] Kódolás utáni átnézés közben talált hibás célútvonal-példa kivizsgálása
      és javítása (2026-08-16) — a `2017-06 Dűne Fro ` album-mappanév
      (kötőjeles `ÉÉÉÉ-HH Esemény` formátum) egyik minta által sem lett
      felismerve, így a fájl tévesen a "nincs album" ágra esett. A teljes
      Takeout-állományon lefuttatott elemzés szerint ez 5 mintázatot és
      **172 fájlt** érintett (kötőjeles nap- és hónap-szintű albumnevek,
      pl. `2016-07 Görögország`, `2017-12-29 Julcsi szalagavató`,
      `2015-12-31 Szilveszter`). Javítva: `DAY_ALBUM_RE` mostantól `_` és
      `-` elválasztót is elfogad, új `MONTH_ALBUM_RE` hozzáadva a
      nap nélküli `ÉÉÉÉ-HH Esemény` mintához, `compute_b2_key()` frissítve.
      A specifikáció (`mappazasi_algoritmus_specifikacio.md`, 2.1 és 3.
      fejezet) és a javítás is leellenőrizve a teszt-ZIP-en (a
      `2017-06 Dűne Fro /20170608_211651(0).jpg` most helyesen
      `Kepek02/2017/06/08-dune-fro/20170608-211651-0.jpg`-re képződik).
- [x] Fennmaradó fel nem ismert mappanév-típusok tisztázása és lezárása
      (2026-08-16) — a teljes elemzésben talált 3 további mintázatról
      egyenként döntés született:
      - dátum-előtag nélküli, tisztán szöveges albumnév (pl. `karácsony`)
        → **implementálva**, negyedik mintaként (`match_named_album`
        "text" ága), pl. `karácsony/20171225_143022.jpg` most
        `Kepek02/2017/12/25-karacsony/20171225-143022.jpg`-re képződik.
        Kizárva belőle: puszta számjegyekből álló mappanév és `@`-ot
        tartalmazó mappanév (l. alább).
      - megosztott, más Google-fiókból importált album mappaneve
        (`11Titkár, tuskecsaladikepek@gmail.com`) → **szándékosan
        figyelmen kívül hagyva** (technikai/fiók-azonosító jellegű név,
        nem valódi esemény-név).
      - puszta évszám esemény-szöveg nélkül (`2015`) → **szándékosan
        figyelmen kívül hagyva** (elhanyagolható, egyedi eset).
      Mindhárom eset egységtesztekkel leellenőrizve (`match_named_album`
      + `compute_b2_key` közvetlen hívásával), a specifikáció frissítve.
- [ ] Dry-run eredmény közös átnézése (helyes-e a kiszámolt célútvonal
      minden sornál, ésszerű-e a "már fent van" / "feltöltésre kerülne" arány)
      — a `feltoltes_terv_takeout-2017-20260331T162139Z-3-001.csv` most már
      olvasható **és** a fenti javítást tartalmazza, ellenőrzésre kész
- [ ] Ha a dry-run rendben van: **első éles teszt** ugyanezen a kis ZIP-en
      (`--dry-run` nélkül), utána ellenőrzés a B2-n (Dashboard vagy `rclone lsf`)
- [ ] Ha az éles teszt is jó: eldönteni, hogyan fussunk végig a többi
      (nagyobb) Takeout ZIP-en — egyenként kézzel, vagy egy összefogó
      "az összes ZIP-et végigfuttató" wrapper script írása

### Prioritási sorrend a ZIP-ekhez (2026-08-16-i egyeztetés alapján)

A `takeout_b2_teljes_egyeztetes.csv` ZIP-enkénti csoportosítása megmutatta,
mely Takeout ZIP-ek hiányoznak legnagyobb arányban a B2-ről — ez alapján
érdemes sorrendben végigmenni rajtuk (legsürgősebb elöl):

| Sorrend | ZIP | Hiányzó | Hiányzó arány |
|---|---|---|---|
| 1 | `takeout-2015 képek-20251230T080324Z-3-001.zip` | 613 / 662 | **92,6%** |
| 2 | `takeout-2015 képek-20251230T080324Z-3-002.zip` | 660 / 785 | **84,1%** |
| 3 | `takeout-2017-20260331T162139Z-3-001.zip` (**teszt-ZIP**) | 497 / 669 | 74,3% |
| 4 | `takeout-2015 képek-20251230T080324Z-3-003.zip` | 572 / 779 | 73,4% |
| 5 | `takeout-2015 képek-20251230T080324Z-3-004.zip` | 761 / 1054 | 72,2% |
| 6 | `takeout-2021-20260131T161119Z-3-003.zip` | 50 / 132 | 37,9% |
| 7 | `takeout-2011 képek-20251227T152935Z-3-001.zip` | 1042 / 3292 | 31,7% |
| 8 | `takeout-2021-20260131T161119Z-3-002.zip` | 47 / 173 | 27,2% |
| 9 | `takeout-2021-20260131T161119Z-3-001.zip` | 50 / 206 | 24,3% |
| 10 | `takeout-2016 fényképek-20251230T080513Z-3-001.zip` | 13 / 129 | 10,1% |

**Következtetés**: a 4 db "takeout-2015 képek" ZIP (1–2., 4–5. hely) valószínűleg
**soha nem lett feltöltve** — ezek a legmagasabb prioritásúak, miután a
`takeout_to_b2_feltoltes.py` bevált a teszten.
- [ ] `takeout_to_b2_feltoltes.py` és a teszt-segédfájlok **git commit**-ja
      (jelenleg még nincs commitolva, mert nincs tesztelve)
- [ ] Végül: a 4 362 hiányzó fájl tényleges pótlása (a fenti eszközzel,
      vagy a `takeout_b2_teljes_egyeztetes.csv` "hianyzik-b2-rol" sorai
      alapján kiválasztott releváns Takeout ZIP-ek végigfuttatásával)

## Nyitott, még nem eldöntött kérdések

- Mi legyen a több, egymástól eltérő nevű albumban is szereplő fájlokkal
  (l. `mappazasi_algoritmus_specifikacio.md` 3. fejezet, "Ismert korlátok")?
- A régi B2-tartalom kb. 62%-a olyan útvonalon van, amit semmilyen
  tesztelt szabály nem magyaráz (feltehetően emberi elgépelés/tévedés a
  kézi rendezés során) — ezekkel nem foglalkozunk visszamenőleg, csak az
  új feltöltéseknél alkalmazzuk a specifikációt.
De lehet írni