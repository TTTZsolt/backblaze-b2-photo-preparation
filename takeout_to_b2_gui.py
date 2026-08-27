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
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from takeout_to_b2_feltoltes import process_zip

DEFAULT_TAKEOUT_DIR = r"C:\Users\zsolt.tuske\Pictures\Takeout"


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
        self.log_queue = queue.Queue()
        self.worker_running = False

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

    def pick_file(self):
        initial_dir = DEFAULT_TAKEOUT_DIR if os.path.isdir(DEFAULT_TAKEOUT_DIR) else os.path.expanduser("~")
        path = filedialog.askopenfilename(
            title="V\u00e1laszd ki a Takeout ZIP f\u00e1jlt",
            initialdir=initial_dir,
            filetypes=[("ZIP f\u00e1jlok", "*.zip"), ("Minden f\u00e1jl", "*.*")],
        )
        if not path:
            return
        self.zip_path = path
        self.path_label.config(text=path, fg="#111")
        self.start_btn.config(state="normal")

    def start(self):
        if self.worker_running or not self.zip_path:
            return
        self.worker_running = True
        self.pick_btn.config(state="disabled")
        self.start_btn.config(state="disabled")
        self.log_text.delete("1.0", "end")
        dry_run = self.dry_run_var.get()
        self.status_label.config(text="Feldolgoz\u00e1s foly\u00e1ban...", fg="#b45309")

        thread = threading.Thread(target=self._run_worker, args=(self.zip_path, dry_run), daemon=True)
        thread.start()

    def _run_worker(self, zip_path, dry_run):
        writer = QueueWriter(self.log_queue)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = writer
        sys.stderr = writer
        error = None
        try:
            process_zip(zip_path, dry_run=dry_run)
        except Exception as e:
            import traceback
            error = e
            traceback.print_exc()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.log_queue.put(("__DONE__", error))

    def poll_log_queue(self):
        try:
            while True:
                item = self.log_queue.get_nowait()
                if isinstance(item, tuple) and item and item[0] == "__DONE__":
                    self.on_worker_done(item[1])
                else:
                    self.log_text.insert("end", item)
                    self.log_text.see("end")
        except queue.Empty:
            pass
        self.root.after(100, self.poll_log_queue)

    def on_worker_done(self, error):
        self.worker_running = False
        self.pick_btn.config(state="normal")
        self.start_btn.config(state="normal")
        if error:
            self.status_label.config(text="Hiba t\u00f6rt\u00e9nt.", fg="#dc2626")
            messagebox.showerror("Hiba", f"A feldolgoz\u00e1s hib\u00e1val le\u00e1llt:\n{error}")
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
