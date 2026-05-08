# Válogatás Program Specifikáció

Egy terv megalapozása. Hogyan tudom a B2-re felküldeni a fényképeket, némi előkészítést követően úgy, hogy kétszer ne kerülhessen fel ugyanaz a kép.

## 1. Cél

Egyszerűsíteni szeretném a fényképeim előkészítését.

## 2. Jelenlegi folyamat

Nagyon bonyolult és követhetetlen, valami egyszerűbb kellene, de van néhány szempont amit követni szeretnék

1. A fényképeket a Google photo-ból takeout-tal töltöm le az eredeti képek mappáva. Ezt meg is akarom tartani

2. A képeket kicsomagolom a **<u>Feldolgozandó képek</u>** mappába. Itt megkapják azt a mappa struktúrát, ami a google photo-ban volt.  

3. Innét a vagy a FastStone programmal, vagy az általad készített sort_by_date.py programmal át **move**-olom a képeket a <u>Véglegesített könyvtrába</u>, ahol standard módon időrendi (Év/hónap/esemény(opcionális)) besorolást kapják.

4. Innét a **prepare_photos.py** programmal a karaktereket szabványosítom,  bemásolom (lehet, hogy move-olni kellene) az elokeszitett_kepek alá, majd copy update paranccsal másolom fel a B2-re egy egy lépésben. Mind az elokeszitett_kepek alá másolás, mind a B2-re másolás fel van arra készítve, hogy a korábban / B2-re másolt képeket átugorja a program. Az update miatt a B2-n javított képek sem kerülnek felülírásra, mert csak a lokálisan későbbi dátumú file-okat másolja fel.
