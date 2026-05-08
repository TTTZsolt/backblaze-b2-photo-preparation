# Tesztterv: Duplikáció elleni védelem ellenőrzése

Ez a dokumentum leírja azokat a teszteseteket, amelyekkel igazolható, hogy a rendszer elkerüli a felesleges fájlfeldolgozást és a duplikált feltöltéseket a Backblaze B2-re.

## 1. Tesztkörnyezet előkészítése
*   **Forrás mappa:** Egy teszt mappa (pl. `test_images`), benne 2-3 mintaképpel.
*   **Véglegesített mappa:** A `c:\Users\zsolt.tuske\Pictures\Véglegesített képek` mappa.
*   **B2 Vödör:** `Kepek02` és `kepek02-thumbs`.

---

## 2. Tesztesetek

### T1: Helyi szintű duplikáció (Skip logic)
*   **Cél:** Igazolni, hogy a `prepare_photos.py` nem dolgozza fel újra azt, ami már kész van.
*   **Lépések:**
    1.  Futtasd a `prepare_photos.py`-t.
    2.  Ellenőrizd, hogy a fájlok létrejöttek az `elokeszitett_kepek` mappában.
    3.  Futtasd le újra a scriptet változtatás nélkül.
*   **Várt eredmény:** A második futásnál minden fájl mellé az **"Atugorva (mar letezik)"** üzenet kerül. Nem készül új thumbnail.

### T2: Rclone szintű duplikáció (Feltöltés kihagyása)
*   **Cél:** Igazolni, hogy az `rclone` nem tölti fel újra azt, ami már fenn van a felhőben.
*   **Lépések:**
    1.  Futtasd a `prepare_photos.py`-t (ez elvégzi a feltöltést is).
    2.  Várj, amíg befejeződik.
    3.  Futtasd le újra.
*   **Várt eredmény:** Az `rclone` kimenetén a **"Checks: X / X"** értéke meglesz, de a **"Transferred: 0"** lesz (vagy csak a nagyon kicsi metaadat fájlok mennek át).

### T3: Ékezetes és speciális karakterek ütközése
*   **Cél:** Igazolni, hogy a különböző elnevezésű, de tisztítva azonos nevű fájlok nem okoznak duplikációt.
*   **Lépések:**
    1.  Helyezz a forrásba két fájlt: `Kép Árvíz.jpg` és `kep-arviz.jpg`.
    2.  Futtasd a scriptet.
*   **Várt eredmény:** Csak egy fájl jön létre az előkészített mappában (`kep-arviz.jpg`), a másodiknál a rendszer észleli a névütközést és átugorja (vagy sorszámozza, a beállítástól függően).

### T4: HEIC konverzió ismételt ellenőrzése
*   **Cél:** Igazolni, hogy a HEIC->JPG konverzió után a rendszer felismeri a már meglévő JPG-t.
*   **Lépések:**
    1.  Futtass le egy HEIC fájlt.
    2.  Ellenőrizd a létrejött JPG-t.
    3.  Futtasd újra a scriptet.
*   **Várt eredmény:** A rendszer felismeri, hogy a HEIC-hez tartozó cél JPG már létezik, és átugorja a konverziót.

### T5: B2 Életciklus (Verzió tisztítás)
*   **Cél:** Igazolni, hogy a felhőben nem halmozódnak a régi változatok.
*   **Lépések:**
    1.  Tölts fel egy képet.
    2.  Módosítsd a képet (vagy a metaadatát a Képnézegetőben).
    3.  Töltsd fel/mentsd el újra.
    4.  Ellenőrizd a Backblaze webes felületén a "Show History" gombbal.
*   **Várt eredmény:** Az új verzió látható, a régi pedig 1 nap után automatikusan törlésre kerül (vagy azonnal "Hidden" állapotba kerül).

---

## 3. Kiértékelés
Ha minden teszteset a várt eredményt hozza, a rendszer duplikációmentesnek tekinthető.

---

## 4. Tesztelési Napló

Ebben a táblázatban rögzítheted a lefutott teszteket és azok eredményeit.

| Dátum | Verzió | Teszteset (ID) | Művelet / Megjegyzés | Eredmény (OK/Hiba) |
|:------|:-------|:---------------|:---------------------|:-------------------|
| 2026.05.08 | V1.2 | T1, T2 | Első futtatás 2007-es képekkel | OK |
| 2026.05.08 | V1.2 | T1, T2 | Ismételt futtatás (duplikáció ellenőrzés) | OK |
| | | | | |
| | | | | |
