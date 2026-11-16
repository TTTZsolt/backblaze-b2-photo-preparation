"""
Egyszeru grafikus felulet a takeout_to_b2_feltoltes.py-hoz - nincs tobbe
PowerShell-szerkesztes: inditaskor egy fajlvalasztoval kivalasztod a Takeout
ZIP-et, es a mar meglevo feltoltesi logika (SHA1-dedup, szerkesztett-valtozat
szures, album-alapu celutvonal-szamitas) fut le ra, elo naplo-kiirassal.

Hasznalat:
    python takeout_to_b2_gui.py
  (vagy a "Takeout_B2_Feltolto_Inditasa.bat" dupla-kattintassal, konzolablak
  nelkul)
"""

import os
import sys
import json
import shutil
import queue
import threading
import subprocess
import importlib.util
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# A NAS-on lévő Takeout-mappa (alatta évenkénti almappák). Ha elérhető, a
# fájlválasztó itt nyílik meg - hacsak nincs utoljára használt mappa.
NAS_TAKEOUT_DIR = r"X:\Pictures\takeout"

# Ennek a nevű rclone-remote-nak kell léteznie minden gépen (takeout_to_b2_feltoltes.py)
REQUIRED_RCLONE_REMOTE = "b2_storage"

# Gépenkénti beállítás (NEM a Drive-on, hogy a gépek ne írják felül egymást)
SETTINGS_FILE = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                             "takeout_b2_feltolto.json")


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False)
    except OSError:
        pass


def check_environment():
    """Visszaadja a hiányzó dolgok magyar nyelvű listáját (üres lista = minden rendben).
    Nem importálja a feltöltő modult, ezért hiányzó csomag esetén sem omlik össze."""
    problems = []
    for module, pip_name in (("PIL", "Pillow"), ("pillow_heif", "pillow-heif")):
        if importlib.util.find_spec(module) is None:
            problems.append(f"Hiányzik a Python-csomag: {pip_name}. Futtasd a "
                            f"Takeout_B2_Telepites.bat fájlt (vagy: pip install {pip_name}).")
    if shutil.which("rclone") is None:
        problems.append("Az rclone nincs telepítve, vagy nincs a PATH-ban (https://rclone.org/downloads/).")
    else:
        try:
            out = subprocess.run(["rclone", "listremotes"], capture_output=True, text=True,
                                 timeout=30, creationflags=subprocess.CREATE_NO_WINDOW).stdout
            if f"{REQUIRED_RCLONE_REMOTE}:" not in out.split():
                problems.append(f"Nincs '{REQUIRED_RCLONE_REMOTE}' nevű rclone-remote ezen a gépen. "
                                f"Állítsd be: rclone config  (típus: Backblaze B2, név: {REQUIRED_RCLONE_REMOTE}).")
        except (OSError, subprocess.SubprocessError):
            problems.append("Az rclone nem futtatható (rclone listremotes hibázott).")
    return problems


class QueueWriter:
    """Minden write()-ot egy szalbiztos sorba tesz, amit a fo szal (Tk loop)
    olvas ki - igy a hatterben futo feltoltes biztonsagosan irhat a naplo-
    dobozba anelkul, hogy kozvetlenul Tk-widgetet erne el mas szalbol."""

    def __init__(self, q):
        self.q = q

    def write(self, msg):
        if msg:
            self.q.put(msg)

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        root.title("Takeout \u2192 B2 Felt\u00f6lt\u0151")
        root.geometry("820x560")

        self.zip_path = None
        self.settings = load_settings()
        self.env_ok = False
        self.log_queue = queue.Queue()
        self.worker_running = False
        self.result_csv = None

        top = tk.Frame(root, padx=12, pady=12)
        top.pack(fill="x")

        self.pick_btn = tk.Button(top, text="Takeout ZIP kiv\u00e1laszt\u00e1sa...", command=self.pick_file, width=28)
        self.pick_btn.grid(row=0, column=0, sticky="w")

        self.path_label = tk.Label(top, text="Nincs kiv\u00e1lasztott f\u00e1jl.", anchor="w", fg="#555")
        self.path_label.grid(row=0, column=1, sticky="we", padx=(10, 0))
        top.columnconfigure(1, weight=1)

        self.dry_run_var = tk.BooleanVar(value=False)
        dry_chk = tk.Checkbutton(top, text="Csak teszt (dry-run) - nem t\u00f6lt fel semmit, csak ki\u00edrja, mit tenne",
                                  variable=self.dry_run_var)
        dry_chk.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        self.start_btn = tk.Button(top, text="Ind\u00edt\u00e1s", command=self.start, width=20,
                                    state="disabled", bg="#4f46e5", fg="white")
        self.start_btn.grid(row=2, column=0, sticky="w", pady=(10, 0))

        self.status_label = tk.Label(top, text="", anchor="w", fg="#555")
        self.status_label.grid(row=2, column=1, sticky="we", padx=(10, 0))

        self.recheck_btn = tk.Button(top, text="Környezet újraellenőrzése", command=self.run_env_check)
        self.recheck_btn.grid(row=3, column=0, sticky="w", pady=(8, 0))

        self.result_btn = tk.Button(top, text="Eredmény megjelenítése", command=self.show_result,
                                    state="disabled")
        self.result_btn.grid(row=3, column=1, sticky="w", padx=(10, 0), pady=(8, 0))

        # Csak éles futás után aktív, ha a naplóban maradt 'feltoltesi-hiba' sor.
        self.retry_btn = tk.Button(top, text="Hibás fájlok újrapróbálása", command=self.retry_failed,
                                   state="disabled", bg="#b45309", fg="white", disabledforeground="#ddd")
        self.retry_btn.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.retry_zip = None  # a ZIP, amelyhez a legutóbbi éles napló tartozik

        log_frame = tk.Frame(root)
        log_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.log_text = tk.Text(log_frame, wrap="none", font=("Consolas", 9), bg="#111827", fg="#e5e7eb")
        yscroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        xscroll = ttk.Scrollbar(log_frame, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.log_text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.poll_log_queue()
        self.run_env_check()

    def run_env_check(self):
        problems = check_environment()
        self.env_ok = not problems
        self.log_text.delete("1.0", "end")
        if problems:
            self.log_text.insert("end", "A feltöltés ezen a gépen még nem indítható:\n\n")
            for p in problems:
                self.log_text.insert("end", f"  - {p}\n\n")
            self.status_label.config(text="Hiányos környezet.", fg="#dc2626")
        else:
            self.log_text.insert("end", "Környezet rendben (rclone, b2_storage, Pillow, pillow-heif).\n")
            self.status_label.config(text="", fg="#555")
        self.update_start_state()

    def update_start_state(self):
        ok = self.env_ok and self.zip_path and not self.worker_running
        self.start_btn.config(state="normal" if ok else "disabled")

    def pick_file(self):
        initial_dir = os.path.expanduser("~")
        for candidate in (self.settings.get("last_dir"), NAS_TAKEOUT_DIR):
            if candidate and os.path.isdir(candidate):
                initial_dir = candidate
                break
        path = filedialog.askopenfilename(
            title="V\u00e1laszd ki a Takeout ZIP f\u00e1jlt",
            initialdir=initial_dir,
            filetypes=[("ZIP f\u00e1jlok", "*.zip"), ("Minden f\u00e1jl", "*.*")],
        )
        if not path:
            return
        self.zip_path = path
        self.path_label.config(text=path, fg="#111")
        self.settings["last_dir"] = os.path.dirname(path)
        save_settings(self.settings)
        self.update_start_state()

    def start(self):
        if self.worker_running or not self.zip_path or not self.env_ok:
            return
        dry_run = self.dry_run_var.get()
        self.retry_zip = None if dry_run else self.zip_path
        self._begin_work("Feldolgoz\u00e1s foly\u00e1ban...")
        thread = threading.Thread(target=self._run_worker, args=(self.zip_path, dry_run), daemon=True)
        thread.start()

    def retry_failed(self):
        if self.worker_running or not self.retry_zip or not self.result_csv:
            return
        zip_path, plan_csv = self.retry_zip, self.result_csv
        self._begin_work("Hib\u00e1s f\u00e1jlok \u00fajrapr\u00f3b\u00e1l\u00e1sa folyamatban...")
        thread = threading.Thread(target=self._run_worker, args=(zip_path, False, plan_csv), daemon=True)
        thread.start()

    def _begin_work(self, status_text):
        self.worker_running = True
        for btn in (self.pick_btn, self.recheck_btn, self.start_btn, self.result_btn, self.retry_btn):
            btn.config(state="disabled")
        self.log_text.delete("1.0", "end")
        self.result_csv = None
        self.status_label.config(text=status_text, fg="#b45309")

    def update_retry_state(self):
        failed = 0
        if self.retry_zip and self.result_csv:
            try:
                from takeout_to_b2_feltoltes import count_failed_in_plan
                failed = count_failed_in_plan(self.result_csv)
            except Exception:
                failed = 0
        if failed:
            self.retry_btn.config(state="normal", text=f"Hib\u00e1s f\u00e1jlok \u00fajrapr\u00f3b\u00e1l\u00e1sa ({failed} db)")
        else:
            self.retry_btn.config(state="disabled", text="Hib\u00e1s f\u00e1jlok \u00fajrapr\u00f3b\u00e1l\u00e1sa")
        return failed

    def _run_worker(self, zip_path, dry_run, retry_plan_csv=None):
        writer = QueueWriter(self.log_queue)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = writer
        sys.stderr = writer
        error = None
        result = None
        try:
            # késői import: a környezet-ellenőrzés előbb lefut
            from takeout_to_b2_feltoltes import process_zip, retry_failed
            if retry_plan_csv:
                result = retry_failed(zip_path, retry_plan_csv)
            else:
                result = process_zip(zip_path, dry_run=dry_run)
        except Exception as e:
            import traceback
            error = e
            traceback.print_exc()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.log_queue.put(("__DONE__", error, result))

    def poll_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple) and item and item[0] == "__DONE__":
                    self.on_worker_done(item[1], item[2])
                else:
                    self.log_text.insert("end", item)
                    self.log_text.see("end")
        except queue.Empty:
            pass
        self.root.after(100, self.poll_log_queue)

    def show_result(self):
        """Elindítja az eredmény-megjelenítő programot a legutóbbi naplóhoz."""
        if not self.result_csv or not os.path.exists(self.result_csv):
            messagebox.showwarning("Nincs eredmény", "Nincs megjeleníthető napló.")
            return
        viewer = os.path.join(os.path.dirname(os.path.abspath(__file__)), "takeout_eredmeny_megjelenito.py")
        exe = sys.executable
        if exe.lower().endswith("python.exe"):
            pyw = exe[:-len("python.exe")] + "pythonw.exe"
            exe = pyw if os.path.exists(pyw) else exe
        subprocess.Popen([exe, viewer, self.result_csv], creationflags=subprocess.CREATE_NO_WINDOW)

    def on_worker_done(self, error, result=None):
        self.worker_running = False
        if result and os.path.exists(result):
            self.result_csv = result
            self.result_btn.config(state="normal")
        self.pick_btn.config(state="normal")
        self.recheck_btn.config(state="normal")
        self.update_start_state()
        failed = self.update_retry_state()
        if error:
            self.status_label.config(text="Hiba t\u00f6rt\u00e9nt.", fg="#dc2626")
            messagebox.showerror("Hiba", f"A feldolgoz\u00e1s hib\u00e1val le\u00e1llt:\n{error}")
        elif failed:
            self.status_label.config(text=f"K\u00e9sz, {failed} f\u00e1jl felt\u00f6lt\u00e9se nem siker\u00fclt.", fg="#b45309")
            messagebox.showwarning(
                "K\u00e9sz, hib\u00e1kkal",
                f"A feldolgoz\u00e1s befejez\u0151d\u00f6tt, de {failed} f\u00e1jl felt\u00f6lt\u00e9se nem siker\u00fclt.\n"
                f"A 'Hib\u00e1s f\u00e1jlok \u00fajrapr\u00f3b\u00e1l\u00e1sa' gombbal csak ezeket lehet \u00fajra megpr\u00f3b\u00e1lni.")
        else:
            self.status_label.config(text="K\u00e9sz.", fg="#059669")
            messagebox.showinfo("K\u00e9sz", "A feldolgoz\u00e1s befejez\u0151d\u00f6tt. R\u00e9szletek a fenti napl\u00f3ban.")

    def on_close(self):
        if self.worker_running:
            if not messagebox.askyesno("Bez\u00e1r\u00e1s", "M\u00e9g fut a felt\u00f6lt\u00e9s. Biztosan bez\u00e1rod?"):
                return
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
