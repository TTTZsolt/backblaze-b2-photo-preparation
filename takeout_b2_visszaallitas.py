"""
A takeout_to_b2_feltoltes.py egy futasanak VISSZAVONASA.

A feltolto naploja (feltoltes_terv_<zip neve>.csv) minden fajlnal rogziti az
allapotot es a B2 celutvonalat. Ez a szkript a naplo "feltoltve" sorait
torli a Kepek02 es a kepek02-thumbs vodorbol, vegleges torleskent.

Hasznalat:
    python takeout_b2_visszaallitas.py <naplo.csv>            # DRY-RUN: csak ellenoriz es kiir
    python takeout_b2_visszaallitas.py <naplo.csv> --apply    # tenyleges torles (megerositessel)

Biztonsagi szabalyok:
* Alapbol DRY-RUN: semmit nem torol, csak kiirja, mi torlodne.
* Csak a naplo "feltoltve" sorait erinti. A dry-run naplojaban nincs ilyen
  ("feltoltesre-kerulne"), ott a szkript nem csinal semmit.
* Ha egy celutvonalnak TOBB verzioja van a B2-ben, a fajl KIMARAD: lehet, hogy
  a feltoltes egy mar letezo fajl folott keletkezett, amit nem szabad torolni.
* A Lumina Lomtarat NE hasznald a visszaallitashoz: az a kepeket a "szandekosan
  torolt" listara irna, es a feltolto onnantol sosem toltene fel oket ujra.
* Torles utan a Luminaban egy teljes B2-szinkron veszi ki a sorokat az
  adatbazisbol (a szinkron csak megerositett hianyt kezel torlesnek).
"""

import os
import re
import sys
import csv
import json
import argparse
import tempfile
import subprocess
from collections import Counter

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

B2_REMOTE_PREFIX = "b2_storage"
TARGET_BUCKET = "Kepek02"
TARGET_REMOTE = f"{B2_REMOTE_PREFIX}:{TARGET_BUCKET}"
THUMB_REMOTE = f"{B2_REMOTE_PREFIX}:kepek02-thumbs"

VALID_KEY_RE = re.compile(r"^\d{4}/\d{2}/[^/]+(/[^/]+)*$")
# rclone --b2-versions: a regi verziok neve "nev-v2016-07-04-141003-000.kiterjesztes"
VERSION_SUFFIX_RE = re.compile(r"^(.*)-v\d{4}-\d{2}-\d{2}-\d{6}-\d{3}(\.[^./]*)?$")

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def rclone(args, **kw):
    return subprocess.run(["rclone"] + args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", creationflags=NO_WINDOW, **kw)


def base_name(listed_name):
    """A verzio-utotagos nevbol visszaadja az eredeti nevet (ha nincs utotag, valtozatlan)."""
    m = VERSION_SUFFIX_RE.match(listed_name)
    return (m.group(1) + (m.group(2) or "")) if m else listed_name


def list_versions(remote):
    """{eredeti_nev: verziok_szama} a vodor osszes fajljara, a regi verziokkal egyutt."""
    res = rclone(["lsjson", "--files-only", "--recursive", "--b2-versions", remote])
    if res.returncode != 0:
        raise RuntimeError(f"rclone lsjson hiba ({remote}): {res.stderr.strip()}")
    counts = Counter()
    for item in json.loads(res.stdout):
        counts[base_name(item["Path"])] += 1
    return counts


def main():
    ap = argparse.ArgumentParser(description="A Takeout->B2 feltoltes visszavonasa a naplo alapjan.")
    ap.add_argument("naplo", help="A feltoltes_terv_*.csv naplo utvonala")
    ap.add_argument("--apply", action="store_true", help="Tenyleges torles (alapbol csak dry-run)")
    ap.add_argument("--yes", action="store_true", help="Ne kerjen begepelt megerositest (--apply mellett)")
    args = ap.parse_args()

    with open(args.naplo, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    statuses = Counter(r["statusz"] for r in rows)
    print(f"Naplo: {args.naplo}")
    print("Statuszok: " + ", ".join(f"{k}: {v}" for k, v in statuses.most_common()))

    keys = [r["cel_utvonal"] for r in rows if r["statusz"] == "feltoltve"]
    bad = [k for k in keys if not VALID_KEY_RE.match(k)]
    if bad:
        print(f"HIBA: {len(bad)} celutvonal furcsa alaku (pl. {bad[0]!r}), megallok.")
        return 1
    keys = sorted(set(keys))
    if not keys:
        print("\nNincs 'feltoltve' sor a naploban (valoszinuleg dry-run naplo). Nincs mit torolni.")
        return 0
    print(f"\nTorlesre jelolt (feltoltve) fajlok: {len(keys)}")

    print("Verziok lekerdezese a B2-bol (csak olvasas)...", flush=True)
    main_versions = list_versions(TARGET_REMOTE)
    thumb_versions = list_versions(THUMB_REMOTE)

    safe, versioned, missing = [], [], []
    for k in keys:
        n = main_versions.get(k, 0)
        if n == 0:
            missing.append(k)
        elif n > 1:
            versioned.append(k)
        else:
            safe.append(k)

    print(f"  - biztonsagosan torolheto (1 verzio):             {len(safe)}")
    print(f"  - KIHAGYVA, tobb verzio (lehet korabbi tartalom):  {len(versioned)}")
    print(f"  - nincs meg a B2-ben (mar torolve / nem toltodott fel): {len(missing)}")
    for k in versioned[:10]:
        print(f"      tobb verzio: {k}  ({main_versions[k]} db)")
    thumb_present = sum(1 for k in safe if thumb_versions.get(k, 0) > 0)
    print(f"  - a torolheto fajlokhoz tartozo thumbnail a B2-ben: {thumb_present}/{len(safe)}")

    if not safe:
        print("\nNincs torolheto fajl.")
        return 0

    if not args.apply:
        print("\nDRY-RUN: semmi nem torlodott. Tenyleges torleshez: --apply")
        print("Peldak a torlesre kerulo fajlokbol:")
        for k in safe[:8]:
            print("   ", k)
        return 0

    if not args.yes:
        print(f"\nFIGYELEM: {len(safe)} fajl (+ thumbnail) VEGLEGESEN torlodik a B2-bol.")
        if input("A folytatashoz gepeld be: TORLES   > ").strip() != "TORLES":
            print("Megszakitva, semmi nem torlodott.")
            return 1

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8", newline="\n") as tf:
        tf.write("\n".join(safe) + "\n")
        list_path = tf.name
    try:
        for remote in (TARGET_REMOTE, THUMB_REMOTE):
            print(f"\nTorles: {remote} ...", flush=True)
            res = rclone(["delete", remote, "--files-from", list_path, "--b2-hard-delete", "-v"])
            if res.returncode != 0:
                print(f"HIBA a torlesnel ({remote}): {res.stderr.strip()[-500:]}")
                return 1
            deleted = sum(1 for line in res.stderr.splitlines() if "Deleted" in line)
            print(f"  kesz (rclone 'Deleted' sorok: {deleted})")
    finally:
        os.unlink(list_path)

    print("\nUjraellenorzes...", flush=True)
    after = list_versions(TARGET_REMOTE)
    left = [k for k in safe if after.get(k, 0) > 0]
    print(f"A torolni kert fajlok kozul meg megvan a B2-ben: {len(left)}")
    print("\nKovetkezo lepes: teljes B2-szinkron a Luminaban (az adatbazis-sorokat kivezeti).")
    print("Ne hasznald a Lumina Lomtarat ehhez (az tombstone-t irna).")
    return 0 if not left else 1


if __name__ == "__main__":
    sys.exit(main())
