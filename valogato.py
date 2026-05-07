import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import pillow_heif

# HEIC támogatás inicializálása
pillow_heif.register_heif_opener()

class PhotoSelector:
    def __init__(self, root):
        self.root = root
        self.root.title("Fénykép Válogató v1.0")
        self.root.geometry("1000x800")
        
        self.source_dir = ""
        self.target_dir = "valogatott_kepek"
        self.image_list = []
        self.current_index = 0
        self.selections = {} # path: True (keep) / False (skip)
        
        self.setup_ui()
        self.bind_keys()

    def setup_ui(self):
        # Vezérlő gombok
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        self.btn_open = tk.Button(self.btn_frame, text="Mappa megnyitása", command=self.open_dir)
        self.btn_open.pack(side=tk.LEFT, padx=5)
        
        self.lbl_info = tk.Label(self.btn_frame, text="Nincs mappa kiválasztva")
        self.lbl_info.pack(side=tk.LEFT, padx=20)
        
        self.lbl_progress = tk.Label(self.btn_frame, text="0 / 0")
        self.lbl_progress.pack(side=tk.RIGHT, padx=5)

        # Kép megjelenítő terület
        self.canvas = tk.Canvas(self.root, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Alsó sáv instrukciókkal
        self.status_frame = tk.Frame(self.root)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        tk.Label(self.status_frame, text="[S] vagy [Jobbra]: Megtart | [D] vagy [Balra]: Kihagy | [Z]: Vissza").pack()

    def bind_keys(self):
        self.root.bind("<Right>", lambda e: self.select_image(True))
        self.root.bind("s", lambda e: self.select_image(True))
        self.root.bind("S", lambda e: self.select_image(True))
        
        self.root.bind("<Left>", lambda e: self.select_image(False))
        self.root.bind("d", lambda e: self.select_image(False))
        self.root.bind("D", lambda e: self.select_image(False))
        
        self.root.bind("z", lambda e: self.undo_selection())
        self.root.bind("Z", lambda e: self.undo_selection())

    def open_dir(self):
        directory = filedialog.askdirectory()
        if not directory:
            return
        
        self.source_dir = directory
        self.image_list = []
        valid_extensions = ('.jpg', '.jpeg', '.png', '.heic', '.heif')
        
        for root, dirs, files in os.walk(self.source_dir):
            if self.target_dir in root:
                continue
            for f in files:
                if f.lower().endswith(valid_extensions):
                    self.image_list.append(os.path.join(root, f))
        
        if not self.image_list:
            messagebox.showwarning("Figyelem", "Nem található kép a mappában!")
            return
        
        self.current_index = 0
        self.lbl_info.config(text=f"Mappa: {os.path.basename(directory)}")
        self.show_image()

    def show_image(self):
        if not self.image_list or self.current_index >= len(self.image_list):
            self.finish_selection()
            return
            
        path = self.image_list[self.current_index]
        self.lbl_progress.config(text=f"{self.current_index + 1} / {len(self.image_list)}")
        
        try:
            img = Image.open(path)
            # EXIF forgatás kezelése
            if hasattr(img, '_getexif'):
                exif = img._getexif()
                if exif:
                    orientation = exif.get(0x0112)
                    if orientation == 3: img = img.rotate(180, expand=True)
                    elif orientation == 6: img = img.rotate(270, expand=True)
                    elif orientation == 8: img = img.rotate(90, expand=True)
            
            # Átméretezés a canvas méretéhez
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width < 100: canvas_width = 800 # Default ha még nem rajzolt
            if canvas_height < 100: canvas_height = 600
            
            img.thumbnail((canvas_width, canvas_height))
            self.tk_img = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(canvas_width/2, canvas_height/2, anchor=tk.CENTER, image=self.tk_img)
            self.root.title(f"Válogatás - {os.path.basename(path)}")
        except Exception as e:
            print(f"Hiba a kép betöltésekor ({path}): {e}")
            self.current_index += 1
            self.show_image()

    def select_image(self, keep):
        if self.current_index < len(self.image_list):
            path = self.image_list[self.current_index]
            self.selections[path] = keep
            self.current_index += 1
            self.show_image()

    def undo_selection(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_image()

    def finish_selection(self):
        kept_count = sum(1 for v in self.selections.values() if v)
        if messagebox.askyesno("Kész", f"Válogatás befejezve!\n{kept_count} kép lett megtartva.\nSzeretné átmásolni őket a '{self.target_dir}' mappába?"):
            self.copy_images()

    def copy_images(self):
        target_root = os.path.join(self.source_dir, self.target_dir)
        if not os.path.exists(target_root):
            os.makedirs(target_root)
            
        copied = 0
        for path, keep in self.selections.items():
            if keep:
                rel_path = os.path.relpath(path, self.source_dir)
                dest_path = os.path.join(target_root, rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(path, dest_path)
                copied += 1
        
        messagebox.showinfo("Siker", f"{copied} kép sikeresen átmásolva ide:\n{target_root}")
        self.root.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = PhotoSelector(root)
    # Kis trükk, hogy az ablak mérete már ismert legyen a kép méretezéshez
    root.update()
    root.mainloop()
