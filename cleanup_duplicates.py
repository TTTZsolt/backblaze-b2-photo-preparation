import os
import subprocess
import sys

# Windows konzol kódolás javítása
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError: pass

# Beállítások
source_root = r"c:\Users\zsolt.tuske\Pictures\Véglegesített képek"
prep_root = os.path.join(source_root, "elokeszitett_kepek")
remote_target = "b2_storage:Kepek02"
image_extensions = ('.jpg', '.jpeg', '.png', '.cr2', '.nef')

def cleanup():
    print("--- Duplikalodott eredeti kepek takaritasa (Celtarhely alapjan) ---")
    print(f"Helyi elokeszitett: {prep_root}")
    print(f"B2 cel: {remote_target}")
    print("-" * 60)

    deleted_count = 0

    # Végigmegyünk az előkészített mappán
    for subdir, dirs, files in os.walk(prep_root):
        rel_path = os.path.relpath(subdir, prep_root)
        if rel_path == ".":
            clean_rel_path_slashed = ""
        else:
            clean_rel_path_slashed = rel_path.replace(os.sep, '/')

        # Csak a képfájlokkal foglalkozunk
        images = [f for f in files if f.lower().endswith(image_extensions)]
        if not images: continue

        # Kikeressük a szerkesztett változatokat ebben a mappában
        edited_bases = set()
        for f in images:
            name, ext = os.path.splitext(f)
            l_name = name.lower()
            if l_name.endswith("-szerkesztve"):
                edited_bases.add(l_name[:-12])
            elif l_name.endswith("-szerkesztett"):
                edited_bases.add(l_name[:-13])

        if not edited_bases: continue

        # Megkeressük azokat az eredetiket, amiknek van szerkesztett párjuk
        for f in images:
            name, ext = os.path.splitext(f)
            if name.lower() in edited_bases:
                # Találtunk egy felesleges eredetit!
                
                # 1. Törlés helyben
                local_path = os.path.join(subdir, f)
                try:
                    os.remove(local_path)
                    print(f"Helyi torles: {os.path.join(rel_path, f)}")
                except Exception as e:
                    print(f"Hiba a helyi torlesnel ({f}): {e}")

                # 2. Törlés a B2-ről
                remote_path = f"{remote_target}/{clean_rel_path_slashed}/{f}"
                if clean_rel_path_slashed == "":
                    remote_path = f"{remote_target}/{f}"
                
                print(f"B2 torles: {clean_rel_path_slashed}/{f}...")
                try:
                    subprocess.run(["rclone", "deletefile", remote_path], check=True, capture_output=True)
                    deleted_count += 1
                except subprocess.CalledProcessError as e:
                    print(f"B2 torles hiba ({f}): {e.stderr.decode('utf-8', errors='ignore')}")

    print("-" * 60)
    print(f"Kesz! Osszesen {deleted_count} duplikalt eredeti kep lett eltavolitva.")

if __name__ == "__main__":
    cleanup()
