import subprocess
import json

# A vödrök listája, amiket beállítunk
buckets = [
    "2011-ev",
    "Csaladi-kepek1",
    "Kepek01",
    "Kepek02",
    "forras",
    "forras-thumbs",
    "kepek01-thumbs",
    "kepek02-thumbs",
    "torles-elott",
    "torles-elott-thumbs"
]

# A szabaly: Regi verziok elrejtese azonnal (0 nap), torlese 1 nap utan
lifecycle_rule = {
    "daysFromHidingToDeleting": 1,
    "daysFromUploadingToHiding": None,
    "fileNamePrefix": ""
}

rule_json = json.dumps(lifecycle_rule)

print("--- Backblaze B2 Eletciklus Szabalyok Beallitasa ---")

for bucket in buckets:
    print(f"Beallitas: {bucket}...")
    try:
        # Az uj, javasolt parancs: b2 bucket update <bucketName> --lifecycleRule '<json>'
        cmd = [
            "b2", "bucket", "update",
            bucket,
            "--lifecycle-rule", rule_json
        ]
        subprocess.run(cmd, check=True)
        print(f"  [OK] {bucket} sikeresen beallitva.")
    except subprocess.CalledProcessError:
        print(f"  [HIBA] Nem sikerult beallitani: {bucket}.")
    except FileNotFoundError:
        print("  [HIBA] A 'b2' program nem talalhato. Telepites: pip install b2")
        break

print("\n--- Kesz! ---")
