import os
import subprocess
import sys
import shutil
from PIL import Image
import pillow_heif

# Windows konzol kódolás javítása
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError: pass

pillow_heif.register_heif_opener()

# Beállítások
remote_images = "b2_storage:Kepek02"
remote_thumbs = "b2_storage:kepek02-thumbs"
temp_dir = os.path.join(os.getcwd(), "temp_thumb_work")
thumb_size = (400, 400)
image_extensions = ('.jpg', '.jpeg', '.png', '.cr2', '.nef')

def get_b2_files(target):
    print(f"B2 lista lekerese: {target}...")
    try:
        result = subprocess.run(
            ["rclone", "lsf", "-R", "--files-only", target],
            capture_output=True, text=True, encoding='utf-8', errors='ignore'
        )
        if result.returncode != 0: return set()
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}
    except Exception: return set()

def process_missing_thumbnail(rel_path_no_ext, full_img_path):
    print(f"  -> Feldolgozas: {rel_path_no_ext}")
    
    # Útvonalak
    remote_src = f"{remote_images}/{full_img_path}"
    remote_dst = f"{remote_thumbs}/{rel_path_no_ext}.jpg"
    
    local_img = os.path.join(temp_dir, "temp_source" + os.path.splitext(full_img_path)[1])
    local_thumb = os.path.join(temp_dir, "temp_thumb.jpg")
    
    try:
        # 1. Letöltés B2-ről
        subprocess.run(["rclone", "copyto", remote_src, local_img], check=True, capture_output=True)
        
        # 2. Bélyegkép készítése
        with Image.open(local_img) as img:
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif:
                    orientation = exif.get(0x0112)
                    if orientation == 3: img = img.rotate(180, expand=True)
                    elif orientation == 6: img = img.rotate(270, expand=True)
                    elif orientation == 8: img = img.rotate(90, expand=True)
            
            img.thumbnail(thumb_size, Image.Resampling.LANCZOS)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(local_thumb, "JPEG", quality=75, optimize=True)
        
        # 3. Feltöltés B2-re
        subprocess.run(["rclone", "copyto", local_thumb, remote_dst], check=True, capture_output=True)
        
        # Takarítás
        if os.path.exists(local_img): os.remove(local_img)
        if os.path.exists(local_thumb): os.remove(local_thumb)
        return True
        
    except Exception as e:
        print(f"  - HIBA: {e}")
        return False

def manage_thumbnails():
    print("--- Belyegkepek karbantartasa (Teljesen felho alapu) ---")
    
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # 1. B2 listák
    b2_images = get_b2_files(remote_images)
    b2_thumbs = get_b2_files(remote_thumbs)

    # 2. Nagy képek térképe
    image_map = {} 
    for img_path in b2_images:
        if img_path.lower().endswith(image_extensions):
            base_name = os.path.splitext(img_path)[0]
            image_map[base_name] = img_path

    # --- HIÁNYZÓK PÓTLÁSA ---
    print("\nHianyzo belyegkepek potlasa (letoltes -> keszites -> feltoltes)...")
    uploaded_count = 0
    for base_name, full_img_path in image_map.items():
        expected_thumb = f"{base_name}.jpg"
        if expected_thumb not in b2_thumbs:
            if process_missing_thumbnail(base_name, full_img_path):
                uploaded_count += 1

    # --- FELESLEGESEK TÖRLÉSE ---
    print("\nFelesleges belyegkepek torlese a B2-rol...")
    deleted_count = 0
    for thumb_path in b2_thumbs:
        base_name = os.path.splitext(thumb_path)[0]
        if base_name not in image_map:
            print(f"Torles: {thumb_path}")
            remote_path = f"{remote_thumbs}/{thumb_path}"
            try:
                subprocess.run(["rclone", "deletefile", remote_path], check=True, capture_output=True)
                deleted_count += 1
            except Exception as e:
                print(f"HIBA a torlesnel: {e}")

    # Végső takarítás
    shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n" + "="*40)
    print(f"Kesz! Eredmenyek a B2-n:")
    print(f"- Potolva a felhobol: {uploaded_count} db")
    print(f"- Torolve a felhobol: {deleted_count} db")
    print("="*40)

if __name__ == "__main__":
    manage_thumbnails()
