from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from inventory_feed_tool.app_state import (
    DEFAULT_MARKUP_PERCENT_TEXT,
    DesktopAppState,
    format_validation_messages,
    format_workflow_result,
)
from inventory_feed_tool.models import RunConfiguration
from inventory_feed_tool.run_summary import format_full_run_log, write_run_log
from inventory_feed_tool.validation import MessageSeverity
from inventory_feed_tool.workflows import NewImportInput, NewImportWorkflowResult, run_new_import_workflow


class InventoryFeedToolApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Feed Tool")
        self.minsize(840, 620)

        self.lipseys_path = tk.StringVar()
        self.davidsons_inventory_path = tk.StringVar()
        self.davidsons_quantity_path = tk.StringVar()
        self.output_dir_path = tk.StringVar()
        self.markup_percent = tk.StringVar(value=DEFAULT_MARKUP_PERCENT_TEXT)
        self.include_image_urls = tk.BooleanVar(value=True)
        self.convert_button: ttk.Button | None = None
        self.results_text: tk.Text | None = None

        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.Frame(self, padding=16)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

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
            label="Lipseys CSV",
            variable=self.lipseys_path,
            command=self._choose_lipseys,
        )
        self._file_row(
            inputs,
            row=1,
            label="Davidsons inventory CSV",
            variable=self.davidsons_inventory_path,
            command=self._choose_davidsons_inventory,
        )
        self._file_row(
            inputs,
            row=2,
            label="Davidsons quantity CSV",
            variable=self.davidsons_quantity_path,
            command=self._choose_davidsons_quantity,
        )
        self._file_row(
            inputs,
            row=3,
            label="Output folder",
            variable=self.output_dir_path,
            command=self._choose_output_dir,
        )

        options = ttk.LabelFrame(root, text="Options", padding=12)
        options.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        options.columnconfigure(1, weight=1)

        ttk.Label(options, text="Markup percent").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(options, textvariable=self.markup_percent, width=12).grid(
            row=0,
            column=1,
            sticky="w",
            padx=(12, 8),
            pady=4,
        )
        ttk.Checkbutton(
            options,
            text="Include image URLs",
            variable=self.include_image_urls,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

        results = ttk.LabelFrame(root, text="Results", padding=12)
        results.grid(row=4, column=0, sticky="nsew", pady=(16, 0))
        results.columnconfigure(0, weight=1)
        results.rowconfigure(0, weight=1)

        self.results_text = tk.Text(results, height=12, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(results, orient="vertical", command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        self.results_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._set_results("Select one or more source files and choose an output folder.")

        actions = ttk.Frame(root)
        actions.grid(row=5, column=0, sticky="e", pady=(16, 0))

        self.convert_button = ttk.Button(actions, text="Convert", command=self._convert)
        self.convert_button.grid(row=0, column=0)
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

    def _choose_lipseys(self) -> None:
        self._set_path_from_open_dialog(
            self.lipseys_path,
            "Select Lipseys CSV",
            [("CSV files", "*.csv"), ("All files", "*.*")],
        )

    def _choose_davidsons_inventory(self) -> None:
        self._set_path_from_open_dialog(
            self.davidsons_inventory_path,
            "Select Davidsons inventory CSV",
            [("CSV files", "*.csv"), ("All files", "*.*")],
        )

    def _choose_davidsons_quantity(self) -> None:
        self._set_path_from_open_dialog(
            self.davidsons_quantity_path,
            "Select Davidsons quantity CSV",
            [("CSV files", "*.csv"), ("All files", "*.*")],
        )

    def _choose_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Choose output folder")
        if selected:
            self.output_dir_path.set(selected)

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
            lipseys_csv=self._optional_path(self.lipseys_path.get()),
            davidsons_inventory_csv=self._optional_path(self.davidsons_inventory_path.get()),
            davidsons_quantity_csv=self._optional_path(self.davidsons_quantity_path.get()),
            output_dir=self._optional_path(self.output_dir_path.get()),
            markup_percent_text=self.markup_percent.get(),
            include_image_urls=self.include_image_urls.get(),
        )

    def _convert(self) -> None:
        state = self._current_state()
        validation_messages = state.validation_messages()
        if validation_messages:
            self._set_results(format_validation_messages(validation_messages))
            messagebox.showwarning("Inventory Feed Tool", "Review the validation messages before converting.")
            return

        self._set_convert_enabled(False)
        self._set_results("Running conversion...")
        self.update_idletasks()

        try:
            inputs = state.to_new_import_input()
            configuration = state.to_run_configuration()
            result = run_new_import_workflow(inputs, configuration)
            log_path = self._write_run_log(inputs, configuration, result)
            self._set_results(format_workflow_result(result, log_path=log_path))
            self._show_completion_message(result)
        except Exception as exc:
            self._set_results(f"Unexpected error.\n\n{exc}")
            messagebox.showerror("Inventory Feed Tool", f"Unexpected error: {exc}")
        finally:
            self._set_convert_enabled(True)

    def _write_run_log(
        self,
        inputs: NewImportInput,
        configuration: RunConfiguration,
        result: NewImportWorkflowResult,
    ) -> Path | None:
        if inputs.output_dir is None or result.export_result is None:
            return None

        log_text = format_full_run_log(result, inputs=inputs, configuration=configuration)
        return write_run_log(inputs.output_dir, log_text).path

    def _show_completion_message(self, result: NewImportWorkflowResult) -> None:
        severities = {message.severity for message in result.messages}
        if MessageSeverity.ERROR in severities:
            messagebox.showwarning("Inventory Feed Tool", "Conversion completed with errors. Review the results.")
        elif MessageSeverity.WARNING in severities:
            messagebox.showwarning("Inventory Feed Tool", "Conversion completed with warnings. Review the results.")
        else:
            messagebox.showinfo("Inventory Feed Tool", "Conversion complete.")

    def _set_results(self, text: str) -> None:
        if self.results_text is None:
            return
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", "end")
        self.results_text.insert("1.0", text)
        self.results_text.configure(state="disabled")

    def _set_convert_enabled(self, enabled: bool) -> None:
        if self.convert_button is not None:
            self.convert_button.configure(state="normal" if enabled else "disabled")

    @staticmethod
    def _optional_path(value: str) -> Path | None:
        value = value.strip()
        return Path(value) if value else None


def run() -> None:
    app = InventoryFeedToolApp()
    app.mainloop()
