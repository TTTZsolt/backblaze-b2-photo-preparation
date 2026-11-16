"""
A Takeout -> B2 feltoltes eredmenyenek (feltoltes_terv_<zip>.csv) megjelenitoje.
Osszesito statusz-szamlalok + szurheto, kereshetо tablazat.

Hasznalat:
    python takeout_eredmeny_megjelenito.py "feltoltes_terv_xxx.csv"
  (a feltolto GUI "Eredmeny megjelenitese" gombja is ezt inditja)
"""
import csv
import os
import sys
import tkinter as tk
from tkinter import filedialog, ttk

STATUS_LABELS = {
    "feltoltve": "Feltöltve",
    "feltoltesre-kerulne": "Feltöltésre kerülne (dry-run)",
    "feltoltesi-hiba": "FELTÖLTÉSI HIBA",
    "mar-fent-van": "Már fent volt",
    "lomtarban-van": "A Lomtárban van",
    "szandekosan-torolve-nem-toltjuk-fel": "Korábban véglegesen törölve",
}
STATUS_COLORS = {"feltoltesi-hiba": "#fecaca", "feltoltve": "#d1fae5",
                 "feltoltesre-kerulne": "#dbeafe"}
ALL = "(mind)"


def load_rows(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


class Viewer:
    def __init__(self, root, path):
        self.root = root
        self.rows = []
        root.geometry("1000x620")
        self.summary = tk.Label(root, anchor="w", justify="left", padx=12, pady=8,
                                font=("Segoe UI", 10))
        self.summary.pack(fill="x")

        bar = tk.Frame(root, padx=12)
        bar.pack(fill="x")
        tk.Label(bar, text="Státusz:").pack(side="left")
        self.status_var = tk.StringVar(value=ALL)
        self.combo = ttk.Combobox(bar, textvariable=self.status_var, state="readonly", width=38)
        self.combo.pack(side="left", padx=(4, 12))
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        tk.Label(bar, text="Keresés:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.refresh())
        tk.Entry(bar, textvariable=self.search_var, width=30).pack(side="left", padx=4)
        tk.Button(bar, text="Másik napló...", command=self.pick).pack(side="right")

        frame = tk.Frame(root, padx=12, pady=8)
        frame.pack(fill="both", expand=True)
        cols = ("statusz", "takeout_utvonal", "cel_utvonal")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c, t, w in (("statusz", "Státusz", 190), ("takeout_utvonal", "Takeout útvonal", 450),
                        ("cel_utvonal", "Célútvonal a B2-ben", 300)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        for st, col in STATUS_COLORS.items():
            self.tree.tag_configure(st, background=col)
        ys = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=ys.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        self.load(path)

    def pick(self):
        p = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")],
                                       initialdir=os.path.dirname(os.path.abspath(__file__)))
        if p:
            self.load(p)

    def load(self, path):
        try:
            self.rows = load_rows(path)
        except OSError as e:
            self.summary.config(text=f"A napló nem olvasható: {e}", fg="#dc2626")
            return
        self.root.title(f"Takeout eredmény – {os.path.basename(path)}")
        counts = {}
        for r in self.rows:
            counts[r["statusz"]] = counts.get(r["statusz"], 0) + 1
        lines = [f"Összesen {len(self.rows)} egyedi tartalom:"]
        for st, n in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"   {n:>5}  {STATUS_LABELS.get(st, st)}")
        self.summary.config(text="\n".join(lines),
                            fg="#dc2626" if "feltoltesi-hiba" in counts else "#111")
        self.combo["values"] = [ALL] + [f"{st}" for st in sorted(counts)]
        self.status_var.set(ALL)
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        st = self.status_var.get()
        q = self.search_var.get().strip().lower()
        for r in self.rows:
            if st != ALL and r["statusz"] != st:
                continue
            if q and q not in (r["takeout_utvonal"] + r["cel_utvonal"]).lower():
                continue
            self.tree.insert("", "end", tags=(r["statusz"],),
                             values=(r["statusz"], r["takeout_utvonal"], r["cel_utvonal"]))


if __name__ == "__main__":
    root = tk.Tk()
    path = sys.argv[1] if len(sys.argv) > 1 else filedialog.askopenfilename(
        title="Válaszd ki a feltoltes_terv_*.csv naplót",
        initialdir=os.path.dirname(os.path.abspath(__file__)), filetypes=[("CSV", "*.csv")])
    if not path:
        sys.exit(0)
    Viewer(root, path)
    root.mainloop()
