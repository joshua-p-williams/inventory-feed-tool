from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DesktopAppState:
    """UI-independent state collected by the desktop shell."""

    davidsons_file: Path | None = None
    lipseys_file: Path | None = None
    output_file: Path | None = None

    def selected_source_count(self) -> int:
        return sum(
            1
            for source_file in (self.davidsons_file, self.lipseys_file)
            if source_file is not None
        )

    def validation_messages(self) -> list[str]:
        messages: list[str] = []

        if self.selected_source_count() == 0:
            messages.append("Select at least one distributor feed.")

        for label, source_file in (
            ("Davidsons", self.davidsons_file),
            ("Lipseys", self.lipseys_file),
        ):
            if source_file is not None and not source_file.exists():
                messages.append(f"{label} feed does not exist: {source_file}")

        if self.output_file is None:
            messages.append("Choose an output CSV file.")
        elif self.output_file.suffix.lower() != ".csv":
            messages.append("Output file should use the .csv extension.")

        return messages

    def can_convert(self) -> bool:
        return not self.validation_messages()


def placeholder_conversion_message(state: DesktopAppState) -> str:
    if not state.can_convert():
        return "\n".join(state.validation_messages())

    source_count = state.selected_source_count()
    source_word = "source" if source_count == 1 else "sources"
    return (
        f"Ready to convert {source_count} {source_word} to {state.output_file}.\n"
        "Feed conversion will be added in the ETL engine feature."
    )
