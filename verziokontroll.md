Ez a dokumentum követi a projekt mérföldköveit és fejlesztési szakaszait.

1. Kérlek minden fejlesztési lépésről készíts egy commit-ot magyarázó szöveggel.
2. Mindíg ajánlj fel egy magyarázó szöveget és legyen lehetőségem azt átfogalmazni.
3. Készíts táblázatot a commit-okról egy verzión belül: minden commitnak legyen egysora: verzió szám, commit sorszám, dátum és a commit üzenet.
4. A commit táblázatot a Commit fejezetben helyezd el. a commit-ok időrendben csökkenő sorrendben legyenek, hogy a friss commit legyen a táblázat tetején
5. A fő verziók, dátumuk és magyarázatuk továbbra is a Verziótörténet fejezetben kerüljön felsorolásra. A friss verzió legyen a táblázat tetején

# Verziótörténet

- **V1.7-dev** (2026.11.16): Sikeres feltöltés vagy újrapróbálás után automatikusan elindul a Lumina Képtár (tablet) Kepek02 indexének frissítése, ugyanúgy, mint a Connect menü Resync gombjával. GUI-ban kikapcsolható, parancssorban `--no-lumina-sync`.

- **V1.6** (2026.11.16): Takeout → B2 feltöltő: „Hibás fájlok újrapróbálása” gomb (és `--retry-failed` kapcsoló). Csak a napló `feltoltesi-hiba` sorait tölti fel újra, és a naplót helyben frissíti.

- **V1.5** (2026.08.16): `sort_by_date.py` átalakítása: Google Fotók album-mappanév alapú célmappa-számítás (Év/Hónap/Nap-Eseménynév) a puszta Év/Hónap helyett, tartalom-hash (SHA1) alapú duplikátum-felismerés és `--dry-run` biztonsági kapcsoló. Lásd `mappazasi_algoritmus_specifikacio.md`.
- **V1.4** (2026.05.08): Teljes szinkronizáció helyreállítása (110/110 mappa), bélyegkép-ellenőrzés integrálása a check_sync-be és a README v1.4-es frissítése.
- **V1.2** (2026.05.08): Thumbnail generálás integrálása, B2 életciklus automatizálás és hibajavítások (duplikációk és rekurzió elleni védelem).

## # Commit-ok

| Verzió | Sorszám | Dátum      | Commit üzenet                                                                                                                       |
|:------ |:------- |:---------- |:----------------------------------------------------------------------------------------------------------------------------------- |
| V1.7-dev | #1  | 2026.11.16 | Feltöltés után a Lumina Kepek02 index automatikus frissítése (POST /b2/sync), kikapcsolható jelölőnégyzet és --no-lumina-sync kapcsoló. |
| V1.6 | #4    | 2026.11.16 | Verzió véglegesítése (V1.6-dev → V1.6), beolvasztás a main ágba. Élesben tesztelve: a 2015-004 ZIP 19 hibás fájlja újrapróbálással felment. |
| V1.6 | #3    | 2026.11.16 | GUI: ZIP kiválasztásakor a korábbi napló betöltése; a hibás fájlok újrapróbálása gomb így régi ZIP-eknél is aktív. |
| V1.6 | #2    | 2026.11.16 | Takeout → B2 feltöltő: hibás fájlok újrapróbálása gomb és --retry-failed kapcsoló, közös upload_one/write_plan_csv segédfüggvények. |
| V1.6 | #1    | 2026.11.16 | Új segédeszközök: eredmény-megjelenítő, B2-visszaállító szkript, telepítő .bat, folyamatábrák; README: új gép beállítása, ZIP-ek helye. |
| V1.5   | #1      | 2026.08.16 | sort_by_date.py: album-név alapú célmappa-algoritmus, SHA1-duplikátum-felismerés, --dry-run kapcsoló hozzáadása.                    |
| V1.4   | #1      | 2026.05.08 | Teljes szinkronizáció helyreállítása, bélyegkép-kezelés és ellenőrzés bővítése.                                                     |
| V1.2   | #8      | 2026.05.08 | Tesztterv kiegészítése a futtatandó paranccsal.                                                                                     |
| V1.2   | #7      | 2026.05.08 | Tesztnapló sablon frissítése és átnevezése V1.2_C6-ra.                                                                              |
| V1.2   | #6      | 2026.05.08 | Tesztnapló külön fájlba mozgatása (V1.2_C5).                                                                                        |
| V1.2   | #5      | 2026.05.08 | Tesztterv bővítése tesztelési naplóval.                                                                                             |
| V1.2   | #4      | 2026.05.08 | Rclone feltöltési naplózás finomhangolása (részletes nagy képek, tömör thumbnail lista).                                            |
| V1.2   | #3      | 2026.05.08 | Tesztterv létrehozása a duplikáció elleni védelem ellenőrzésére.                                                                    |
| V1.2   | #2      | 2026.05.08 | Dokumentáció frissítése az új feltöltési elvekkel és folyamatokkal.                                                                 |
| V1.2   | #1      | 2026.05.07 | Véglegesített könyvtárban elhelyezett képekből Thumbnail generálás majd B2-be töltés úgy, hogy ne lehessen duplikált kép feltöltés. |

Első teszt: 2007 feltöltése

Második teszt: 2008 feltöltése (ami már fenn van)
