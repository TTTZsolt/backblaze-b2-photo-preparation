import os
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
import pillow_heif

# Windows konzol kódolás javítása
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError: pass

# HEIC támogatás inicializálása
pillow_heif.register_heif_opener()

# Beállítások
source_root = r"c:\Users\zsolt.tuske\Pictures\Véglegesített képek"
prep_root = os.path.join(source_root, "elokeszitett_kepek")
thumb_root = os.path.join(source_root, "elokeszitett_thumbnails")
remote_target = "b2_storage:Kepek02"
remote_thumbs = "b2_storage:kepek02-thumbs"
valid_extensions = ('.jpg', '.jpeg', '.png', '.cr2', '.nef', '.heic', '.heif')
prep_extensions = ('.jpg', '.jpeg', '.png', '.cr2', '.nef')

def clean_string(text):
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])
    text = text.lower()
    text = re.sub(r'[^a-z0-9.]', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def get_b2_counts(target):
    print(f"B2 fajllista lekerese: {target}...")
    try:
        result = subprocess.run(
            ["rclone", "lsf", "-R", "--files-only", target],
            capture_output=True, text=True, encoding='utf-8', errors='ignore'
        )
        if result.returncode != 0: return {}
        counts = defaultdict(int)
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line: continue
            if '/' in line:
                directory = line.rsplit('/', 1)[0]
                counts[directory] += 1
            else:
                counts[""] += 1
        return counts
    except Exception: return {}

def check_sync():
    print("Minden mappa ellenorzese folyamatban (Nagy kepek es Thumbnail-ek)...")
    b2_img_counts = get_b2_counts(remote_target)
    b2_thumb_counts = get_b2_counts(remote_thumbs)
    
    results = []
    
    for subdir, dirs, files in os.walk(source_root):
        if any(x in subdir for x in ["elokeszitett_kepek", "elokeszitett_thumbnails", "kepek02"]):
            continue

        rel_path = os.path.relpath(subdir, source_root)
        if rel_path == ".": rel_path = ""
        
        path_parts = rel_path.split(os.sep) if rel_path else []
        clean_parts = [clean_string(part) for part in path_parts]
        clean_rel_path_slashed = "/".join(clean_parts)
        clean_rel_path_os = os.sep.join(clean_parts)

        # 1. Forrás képek (szerkesztettek figyelembevételével)
        source_images = [f for f in files if f.lower().endswith(valid_extensions)]
        if not source_images: continue
            
        edited_bases = set()
        for f in source_images:
            name, ext = os.path.splitext(f)
            l_name = name.lower()
            if l_name.endswith("-szerkesztve"):
                edited_bases.add(l_name[:-12])
            elif l_name.endswith("-szerkesztett"):
                edited_bases.add(l_name[:-13])
        
        final_source_count = 0
        for f in source_images:
            name, ext = os.path.splitext(f)
            if name.lower() in edited_bases: continue
            final_source_count += 1

        # 2. Nagy képek (Helyi és B2)
        current_prep_dir = os.path.join(prep_root, clean_rel_path_os)
        prep_count = 0
        if os.path.exists(current_prep_dir):
            prep_count = len([f for f in os.listdir(current_prep_dir) 
                             if os.path.isfile(os.path.join(current_prep_dir, f)) 
                             and f.lower().endswith(prep_extensions)])
        b2_img_count = b2_img_counts.get(clean_rel_path_slashed, 0)

        # 3. Thumbnail-ek (Helyi és B2)
        current_thumb_dir = os.path.join(thumb_root, clean_rel_path_os)
        local_thumb_count = 0
        if os.path.exists(current_thumb_dir):
            local_thumb_count = len([f for f in os.listdir(current_thumb_dir) 
                                    if os.path.isfile(os.path.join(current_thumb_dir, f)) 
                                    and f.lower().endswith(('.jpg', '.jpeg'))])
        b2_thumb_count = b2_thumb_counts.get(clean_rel_path_slashed, 0)

        # Ellenőrizzük az eltérést (mindennek meg kell egyeznie a source_count-tal)
        has_diff = (prep_count != final_source_count or 
                    b2_img_count != final_source_count or 
                    local_thumb_count != final_source_count or 
                    b2_thumb_count != final_source_count)

        results.append({
            "mappa": rel_path if rel_path else "[ROOT]",
            "source": final_source_count,
            "prep": prep_count,
            "b2_img": b2_img_count,
            "local_thumb": local_thumb_count,
            "b2_thumb": b2_thumb_count,
            "diff": has_diff
        })

    discrepancies = [r for r in results if r['diff']]
    
    if not discrepancies:
        print("\nGratulalok! Minden mappa (%d db) es az osszes thumbnail is tokeletesen szinkronban van." % len(results))
    else:
        print("\nTALALT ELTERESEK (%d mappaban):" % len(discrepancies))
        header = f"{'Konyvtar':<35} | {'Forras':<6} | {'Helyi':<6} | {'B2':<6} | {'H.Thumb':<7} | {'B2.Thumb':<7}"
        print(header)
        print("-" * len(header))
        for r in discrepancies:
            print(f"{r['mappa']:<35} | {r['source']:<6} | {r['prep']:<6} | {r['b2_img']:<6} | {r['local_thumb']:<7} | {r['b2_thumb']:<7}")
        
        print("\n(A tobbi %d mappa rendben van.)" % (len(results) - len(discrepancies)))

if __name__ == "__main__":
    check_sync()
