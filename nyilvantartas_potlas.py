"""
Egyszeri pótlás: a nyilvántartás (feltoltesi_nyilvantartas.csv) bevezetése
előtti futásokat a meglévő feltoltes_terv_*.csv naplókból veszi fel.

Használat:
    python nyilvantartas_potlas.py            (próbaüzem: csak kiírja, mit venne fel)
    python nyilvantartas_potlas.py --iras     (ténylegesen beírja a nyilvántartásba)

- Mód: ha a naplóban van 'feltoltve' vagy 'feltoltesi-hiba' sor -> eles,
  ha csak 'feltoltesre-kerulne' -> proba.
- Időpont: a napló utolsó módosítási ideje; gép: "ismeretlen (pótolva)".
- A számok a napló MOSTANI állapotát mutatják: ha a hibás fájlokat azóta
  újrapróbáltad, a napló már a javított állapotot tartalmazza.
- A ZIP útvonalát és méretét a NAS Takeout-mappájában keresi meg (név alapján).
- Azt a ZIP-et, amelyhez már van sor a nyilvántartásban, kihagyja - így
  többször futtatva sem duplikál.
"""

import os
import sys
import csv
import glob
import argparse
from collections import Counter
from datetime import datetime

import takeout_to_b2_feltoltes as t

NAS_TAKEOUT_DIR = r"X:\Pictures\takeout"
PREFIX = "feltoltes_terv_"


def find_zip(zip_name):
    if os.path.isdir(NAS_TAKEOUT_DIR):
        for root, _dirs, files in os.walk(NAS_TAKEOUT_DIR):
            if zip_name in files:
                return os.path.join(root, zip_name)
    return None


def main():
    ap = argparse.ArgumentParser(description="Régi feltöltési naplók felvétele a nyilvántartásba.")
    ap.add_argument("--iras", action="store_true", help="Ténylegesen írja a nyilvántartást.")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    already = {r.get("zip_nev") for r in t.read_registry()}
    logs = sorted(glob.glob(os.path.join(here, PREFIX + "*.csv")), key=os.path.getmtime)
    print(f"{'ÍRÁS' if args.iras else 'PRÓBAÜZEM (nem ír semmit)'} - {len(logs)} napló\n")

    added = 0
    for log in logs:
        base = os.path.basename(log)[len(PREFIX):-len(".csv")]
        dry_file = base.endswith("_proba")
        zip_name = (base[:-len("_proba")] if dry_file else base) + ".zip"
        if zip_name in already:
            print(f"KIHAGYVA (már szerepel): {zip_name}")
            continue
        with open(log, newline="", encoding="utf-8") as f:
            st = Counter(r.get("statusz") for r in csv.DictReader(f))
        live = (st["feltoltve"] + st[t.FAILED_STATUS]) > 0 and not dry_file
        mode = t.MODE_LIVE if live else t.MODE_DRY
        counts = {
            "egyedi_tartalom": sum(st.values()),
            "mar_fent": st["mar-fent-van"],
            "lomtarban": st["lomtarban-van"],
            "szandekosan_torolt": st["szandekosan-torolve-nem-toltjuk-fel"],
            "feltoltesre_szant": (st["feltoltve"] + st[t.FAILED_STATUS]) if live else st["feltoltesre-kerulne"],
            "sikeres": st["feltoltve"] if live else "",
            "hibas": st[t.FAILED_STATUS] if live else "",
        }
        when = datetime.fromtimestamp(os.path.getmtime(log)).strftime("%Y-%m-%d %H:%M:%S")
        zip_path = find_zip(zip_name)
        overrides = {"idopont": when, "gep": "ismeretlen (pótolva)", "verzio": "pótolva"}
        if not zip_path:
            zip_path = zip_name  # nem található: csak a név kerül be, méret nélkül
            overrides["zip_utvonal"] = ""
        print(f"{when}  {mode:6}  {zip_name}")
        print(f"      egyedi {counts['egyedi_tartalom']}, már fent {counts['mar_fent']}, "
              f"lomtár {counts['lomtarban']}, szándékosan törölt {counts['szandekosan_torolt']}, "
              f"feltöltésre szánt {counts['feltoltesre_szant']}, sikeres {'-' if not live else counts['sikeres']}, "
              f"hibás {'-' if not live else counts['hibas']}")
        print(f"      ZIP: {zip_path if overrides.get('zip_utvonal') != '' else 'NEM TALÁLHATÓ a NAS-on'}")
        if args.iras:
            if t.append_registry(zip_path, mode, counts, log, overrides=overrides):
                added += 1
    if args.iras:
        print(f"\nBeírva: {added} sor -> {t.registry_path()}")


if __name__ == "__main__":
    main()
