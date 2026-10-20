from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from .core import DocumentError, export_document, find_documents, validate_reference

# Source des valeurs visuelles, documentée dans DESIGN.md.
THEME = json.loads(Path(__file__).with_name("theme.json").read_text(encoding="utf-8"))


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Référence · Word vers PDF")
        self.geometry("920x740")
        self.minsize(660, 640)
        self.configure(background=THEME["background"])
        self.events = queue.Queue()
        self.busy = False
        self.matches: list[Path] = []
        self.search_snapshot = None
        self.page = 0
        self.page_size = 100
        defaults = {"source": r"\\Srv\data", "documents": r"\\srv\gen$\Actes",
                    "pdf": r"\\srv\gen$\Actespdf", "reference": ""}
        self.fields = {key: tk.StringVar(value=value) for key, value in defaults.items()}
        self.status = tk.StringVar(value="Choisissez vos dossiers, puis recherchez une référence.")
        self.output = tk.StringVar(value="Les deux fichiers exportés apparaîtront ici.")
        self.controls = []
        self._style()
        self._build()
        for value in self.fields.values():
            value.trace_add("write", self._invalidate)
        self.after(100, self._poll)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=THEME["background"])
        style.configure("TLabel", background=THEME["background"], foreground=THEME["ink"], font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 25, "bold"))
        style.configure("Note.TLabel", foreground=THEME["muted"])
        style.configure("Status.TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 9))
        style.map("TButton", background=[("active", "#D6E4EE")])
        style.configure("Primary.TButton", background=THEME["primary"], foreground=THEME["paper"])
        style.map("Primary.TButton", background=[("disabled", "#D6E4EE"), ("active", "#104766")],
                  foreground=[("disabled", THEME["muted"])])
        style.configure("TEntry", padding=8, font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _button(self, parent, label, command, **options):
        button = ttk.Button(parent, text=label, command=command, cursor="hand2", **options)
        self.controls.append(button)
        return button

    def _build(self):
        main = ttk.Frame(self, padding=24)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(9, weight=1)
        ttk.Label(main, text="Référence", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(main, text="Retrouver un document. Conserver l’original. Exporter une copie et un PDF.",
                  style="Note.TLabel", wraplength=600).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 20))
        labels = [("source", "Dossier source"), ("documents", "Copies Word"), ("pdf", "Fichiers PDF")]
        for row, (key, label) in enumerate(labels, start=2):
            ttk.Label(main, text=label).grid(row=row, column=0, sticky="w", padx=(0, 14), pady=5)
            entry = ttk.Entry(main, textvariable=self.fields[key])
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            self.controls.append(entry)
            self._button(main, "Parcourir…", lambda k=key: self._pick(k)).grid(row=row, column=2, padx=(10, 0))
        ttk.Label(main, text="Nom ou référence").grid(row=5, column=0, sticky="w", pady=(18, 5))
        self.reference_entry = ttk.Entry(main, textvariable=self.fields["reference"])
        self.reference_entry.grid(row=5, column=1, sticky="ew", pady=(18, 5))
        self.reference_entry.bind("<Return>", lambda event: self.search())
        self.controls.append(self.reference_entry)
        self._button(main, "Effacer", self._clear).grid(row=5, column=2, padx=(10, 0), pady=(18, 5))
        ttk.Label(main, text="Exemple : 0680-2026 → 0680-2026.docx + 0680-2026.pdf",
                  style="Note.TLabel").grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 10))
        self._button(main, "Rechercher dans les sous-dossiers", self.search).grid(row=7, column=0, columnspan=3, sticky="w")
        ttk.Label(main, text="Documents trouvés — sélectionnez celui à convertir").grid(row=8, column=0, columnspan=3, sticky="w", pady=(18, 8))
        results = ttk.Frame(main)
        results.grid(row=9, column=0, columnspan=3, sticky="nsew")
        results.columnconfigure(0, weight=1)
        results.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(results, columns=("name", "folder"), show="headings", selectmode="browse", height=5)
        self.tree.heading("name", text="Document Word")
        self.tree.heading("folder", text="Sous-dossier")
        self.tree.column("name", width=450, minwidth=260)
        self.tree.column("folder", width=280, minwidth=180)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(results, orient="vertical", command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(results, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind("<<TreeviewSelect>>", lambda event: self._update_export())
        navigation = ttk.Frame(results)
        navigation.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.previous_button = self._button(navigation, "Précédents", lambda: self._turn_page(-1))
        self.previous_button.pack(side="left")
        self.next_button = self._button(navigation, "Suivants", lambda: self._turn_page(1))
        self.next_button.pack(side="right")
        self.page_label = ttk.Label(navigation, text="Aucun résultat")
        self.page_label.pack(pady=8)
        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.grid(row=10, column=0, columnspan=3, sticky="ew", pady=(12, 6))
        self.status_label = ttk.Label(main, textvariable=self.status, style="Status.TLabel", wraplength=790)
        self.status_label.grid(row=11, column=0, columnspan=3, sticky="w", pady=5)
        self.export_button = self._button(main, "Copier et convertir en PDF", self.export, style="Primary.TButton")
        self.export_button.grid(row=12, column=0, columnspan=3, sticky="w", pady=8)
        ttk.Label(main, textvariable=self.output, style="Note.TLabel", wraplength=790).grid(row=13, column=0, columnspan=3, sticky="w")
        self._update_export()
        self._update_navigation()
        self.bind("<Configure>", self._resize)

    def _resize(self, event):
        if event.widget is self:
            for widget in self.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label) and int(child.cget("wraplength")) > 0:
                        child.configure(wraplength=max(200, event.width - 60))

    def _pick(self, key):
        if directory := filedialog.askdirectory(parent=self, title="Choisir le dossier", mustexist=True):
            self.fields[key].set(directory)

    def _clear(self):
        self.fields["reference"].set("")
        self.reference_entry.focus_set()

    def _invalidate(self, *args):
        self.search_snapshot = None
        self.matches = []
        self.page = 0
        self.tree.delete(*self.tree.get_children())
        self.output.set("Les deux fichiers exportés apparaîtront ici.")
        self._message("Paramètres modifiés. Lancez une recherche pour sélectionner un document.")
        self._update_export()
        self._update_navigation()

    def _update_navigation(self):
        self.previous_button.configure(state="normal" if not self.busy and self.page > 0 else "disabled")
        self.next_button.configure(state="normal" if not self.busy and (self.page + 1) * self.page_size < len(self.matches) else "disabled")
        start = self.page * self.page_size
        self.page_label.configure(text=f"{start + 1}–{min(start + self.page_size, len(self.matches))} sur {len(self.matches)}"
                                  if self.matches else "Aucun résultat")

    def _turn_page(self, direction):
        if not self.busy and 0 <= self.page + direction <= (len(self.matches) - 1) // self.page_size:
            self.page += direction
            self._render_results()

    def _render_results(self):
        self.tree.delete(*self.tree.get_children())
        root = Path(self.search_snapshot[0]).resolve()
        start = self.page * self.page_size
        for index in range(start, min(start + self.page_size, len(self.matches))):
            path = self.matches[index]
            self.tree.insert("", "end", iid=str(index), values=(path.name, str(path.parent.relative_to(root))))
        self._update_navigation()
        self._update_export()

    def _snapshot(self):
        return tuple(self.fields[key].get().strip() for key in ("source", "documents", "pdf", "reference"))

    def _update_export(self):
        self.export_button.configure(state="normal" if not self.busy and self.tree.selection() and self.search_snapshot else "disabled")

    def _message(self, text, error=False):
        self.status.set(text)
        self.status_label.configure(foreground=THEME["error"] if error else THEME["ink"])

    def _work(self, task, function):
        self.busy = True
        for control in self.controls:
            control.configure(state="disabled")
        self.progress.start(12)

        def execute():
            try:
                self.events.put((task, function(), None))
            except Exception as error:
                text = str(error) if isinstance(error, (DocumentError, OSError)) else "Une erreur inattendue est survenue. Relancez la recherche."
                self.events.put((task, None, text))
        threading.Thread(target=execute, daemon=True).start()

    def search(self):
        if self.busy:
            return
        snapshot = self._snapshot()
        try:
            if not snapshot[3]:
                raise DocumentError("Saisissez un nom, un mot ou une référence.")
            if not snapshot[0]:
                raise DocumentError("Choisissez d’abord le dossier source.")
            if any(value and Path(value).expanduser().resolve() == Path(snapshot[0]).expanduser().resolve()
                   for value in snapshot[1:3]):
                raise DocumentError("Les dossiers de sortie doivent être différents du dossier source.")
        except DocumentError as error:
            self._message(str(error), True)
            self.reference_entry.focus_set()
            return
        self._invalidate()
        self._message("Recherche en cours…")
        excluded = tuple(Path(value) for value in snapshot[1:3] if value)
        self._work("search", lambda: (snapshot, find_documents(Path(snapshot[0]), snapshot[3], excluded)))

    def export(self):
        if self.busy or not self.tree.selection() or not self.search_snapshot:
            return
        source, documents, pdf, reference = self._snapshot()
        if not documents or not pdf:
            self._message("Choisissez les deux dossiers de sortie avant de convertir.", True)
            return
        document = self.matches[int(self.tree.selection()[0])]
        try:
            reference = validate_reference(document.stem)
        except DocumentError:
            self._message("Ce document ne commence pas par une référence numéro-année. Aucun nom de sortie ne peut être extrait.", True)
            return
        self._message("Copie et conversion en cours… Les originaux sont conservés.")
        self._work("export", lambda: export_document(document, reference, Path(documents), Path(pdf)))

    def _poll(self):
        try:
            task, result, error = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.progress.stop()
            for control in self.controls:
                control.configure(state="normal")
            if error:
                self._message(error, True)
            elif task == "search":
                self.search_snapshot, self.matches = result
                self._render_results()
                self._message(f"{len(self.matches)} document(s) trouvé(s). Sélectionnez le document à convertir." if self.matches
                              else "Aucun document trouvé. Vérifiez la référence et le dossier source.")
                if len(self.matches) == 1:
                    self.tree.selection_set("0")
                    self.tree.focus("0")
            else:
                self._message("Export terminé. La copie Word et le PDF sont disponibles.")
                self.output.set(f"Word : {result[0]}\nPDF : {result[1]}")
            self._update_export()
            self._update_navigation()
        self.after(100, self._poll)

    def _close(self):
        if self.busy:
            self._message("Une opération est en cours. Attendez sa fin avant de fermer la fenêtre.")
        else:
            self.destroy()


def main():
    Application().mainloop()


if __name__ == "__main__":
    main()
