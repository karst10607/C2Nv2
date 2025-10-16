import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from .config import AppConfig

TITLE = "Notion Importer Settings"

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.cfg = AppConfig.load()
        root.title(TITLE)
        root.geometry("520x260")

        tk.Label(root, text="Notion Token").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.token = tk.Entry(root, width=60, show="")
        self.token.insert(0, self.cfg.notion_token or "")
        self.token.grid(row=0, column=1, padx=8, pady=6)

        tk.Label(root, text="Parent ID (optional)").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.parent = tk.Entry(root, width=60)
        self.parent.insert(0, self.cfg.parent_id or "")
        self.parent.grid(row=1, column=1, padx=8, pady=6)

        tk.Label(root, text="Source HTML Folder").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        self.source = tk.Entry(root, width=60)
        self.source.insert(0, self.cfg.source_dir)
        self.source.grid(row=2, column=1, padx=8, pady=6)
        tk.Button(root, text="Browse", command=self.browse).grid(row=2, column=2, padx=8)

        btns = tk.Frame(root)
        btns.grid(row=3, column=0, columnspan=3, pady=16)
        tk.Button(btns, text="Save", command=self.save).pack(side=tk.LEFT, padx=8)
        tk.Button(btns, text="Close", command=root.destroy).pack(side=tk.LEFT, padx=8)

    def browse(self):
        d = filedialog.askdirectory(initialdir=str(Path(self.source.get()).expanduser()))
        if d:
            self.source.delete(0, tk.END)
            self.source.insert(0, d)

    def save(self):
        self.cfg.notion_token = self.token.get().strip() or None
        self.cfg.parent_id = (self.parent.get().strip() or None)
        self.cfg.source_dir = self.source.get().strip()
        try:
            self.cfg.save()
            messagebox.showinfo(TITLE, f"Saved to {Path.home() / '.notion_importer' / 'config.json'}")
        except Exception as e:
            messagebox.showerror(TITLE, str(e))

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
