from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from inventory_feed_tool.app_state import DesktopAppState, placeholder_conversion_message


class InventoryFeedToolApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Feed Tool")
        self.minsize(720, 460)

        self.davidsons_path = tk.StringVar()
        self.lipseys_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Select source files and choose an output CSV.")

        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.Frame(self, padding=16)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)

        title = ttk.Label(root, text="Inventory Feed Tool", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            root,
            text="Prepare distributor inventory feeds for website product imports.",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 16))

        inputs = ttk.LabelFrame(root, text="Inputs", padding=12)
        inputs.grid(row=2, column=0, sticky="ew")
        inputs.columnconfigure(1, weight=1)

        self._file_row(
            inputs,
            row=0,
            label="Davidsons feed",
            variable=self.davidsons_path,
            command=self._choose_davidsons,
        )
        self._file_row(
            inputs,
            row=1,
            label="Lipseys feed",
            variable=self.lipseys_path,
            command=self._choose_lipseys,
        )
        self._file_row(
            inputs,
            row=2,
            label="GoDaddy output CSV",
            variable=self.output_path,
            command=self._choose_output,
        )

        status = ttk.LabelFrame(root, text="Status", padding=12)
        status.grid(row=3, column=0, sticky="nsew", pady=(16, 0))
        status.columnconfigure(0, weight=1)
        status.rowconfigure(0, weight=1)

        status_label = ttk.Label(
            status,
            textvariable=self.status_text,
            justify="left",
            anchor="nw",
            wraplength=640,
        )
        status_label.grid(row=0, column=0, sticky="nsew")

        actions = ttk.Frame(root)
        actions.grid(row=4, column=0, sticky="e", pady=(16, 0))

        ttk.Button(actions, text="Convert", command=self._convert).grid(row=0, column=0)
        ttk.Button(actions, text="Close", command=self.destroy).grid(row=0, column=1, padx=(8, 0))

    def _file_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        command: Callable[[], None],
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(12, 8),
            pady=4,
        )
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, pady=4)

    def _choose_davidsons(self) -> None:
        self._set_path_from_open_dialog(
            self.davidsons_path,
            "Select Davidsons feed",
            [("Inventory feeds", "*.csv *.xml"), ("All files", "*.*")],
        )

    def _choose_lipseys(self) -> None:
        self._set_path_from_open_dialog(
            self.lipseys_path,
            "Select Lipseys feed",
            [("Inventory feeds", "*.csv"), ("All files", "*.*")],
        )

    def _choose_output(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="Choose GoDaddy output CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self.output_path.set(selected)

    def _set_path_from_open_dialog(
        self,
        variable: tk.StringVar,
        title: str,
        filetypes: list[tuple[str, str]],
    ) -> None:
        selected = filedialog.askopenfilename(title=title, filetypes=filetypes)
        if selected:
            variable.set(selected)

    def _current_state(self) -> DesktopAppState:
        return DesktopAppState(
            davidsons_file=self._optional_path(self.davidsons_path.get()),
            lipseys_file=self._optional_path(self.lipseys_path.get()),
            output_file=self._optional_path(self.output_path.get()),
        )

    def _convert(self) -> None:
        message = placeholder_conversion_message(self._current_state())
        self.status_text.set(message)

        if "will be added" in message:
            messagebox.showinfo("Inventory Feed Tool", message)
        else:
            messagebox.showwarning("Inventory Feed Tool", message)

    @staticmethod
    def _optional_path(value: str) -> Path | None:
        value = value.strip()
        return Path(value) if value else None


def run() -> None:
    app = InventoryFeedToolApp()
    app.mainloop()
