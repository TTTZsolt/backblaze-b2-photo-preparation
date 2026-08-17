# Takeout ↔ B2 egyeztetés (2026-08-15)

## Módszer

A `kepek02` Backblaze B2 vödör teljes tartalmát (fájlnév, méret, SHA1) összevetettem
a `C:\Users\zsolt.tuske\Pictures\Takeout\` mappában található összes ZIP-archívum
és különálló képfájl tartalmának SHA1 lenyomatával — a fájlnév és mappaszerkezet
eltérésétől függetlenül, kizárólag a tényleges bájttartalom alapján.

**Fontos korlát:** csak a `kepek02` vödröt néztem át, a Lomtár (trash) vödröt nem.
Ha egy kép szándékosan törlésre került a válogatás során, az is "hiányzó"-ként
jelenik meg itt, holott az elvárt működés volt. A lenti számok tehát a
re-feltöltendő jelöltek **felső becslése**, nem a tényleges hiba mértéke.

## Összegzés

| | |
|---|---|
| Helyi Takeout médiafájlok (összes bejegyzés) | 7 974 |
| ...ebből egyedi tartalom (SHA1 alapján) | 6 005 |
| Fájlok a `kepek02` vödörben | 4 981 |
| Megtalálva (tartalom egyezik) | 3 480 |
| Gyanús (név egyezik, tartalom nem) | 1 |
| **Hiányzik teljesen (egyedi tartalom)** | **3 833** |
| ...ebből Takeout-album duplikátumokkal együtt | 4 493 bejegyzés |
| Hiányzó tartalom összmérete | 11,6 GB |

## Részletes lista

A 3 833 hiányzó fájl teljes, kereshető listája itt található:
`takeout_b2_hianyzo_2026-08-15.csv` (ugyanebben a mappában).

Oszlopok: fájlnév, méret, előfordulások száma a Takeout-ban, SHA1, forrás útvonalak
(ZIP név + belső útvonal, `|` -vel elválasztva, ha többször is szerepel).

## Online riport

Egy kereshető/rendezhető, interaktív változat is elérhető:
https://claude.ai/code/artifact/d01b92ed-420b-4c56-b7a4-b7e78d4aee36

## Következő lépés (nyitott kérdés)

A Lomtár (trash) vödör át nincs még ellenőrizve — érdemes lehet azt is átnézni,
hogy leszűkítsük a listát a ténylegesen újra feltöltendő képekre (kiszűrve azokat,
amiket szándékosan töröltél a válogatás során).
