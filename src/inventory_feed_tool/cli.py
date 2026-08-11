from __future__ import annotations

import argparse
from pathlib import Path

from inventory_feed_tool import __version__
from inventory_feed_tool.workflows import NewImportInput, run_new_import_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inventory-feed-tool",
        description="Convert distributor inventory feeds into website import files.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    new_import = subparsers.add_parser(
        "new-import",
        help="Convert distributor feed files into GoDaddy new-import CSV batches.",
    )
    new_import.add_argument("--lipseys-csv", type=Path, help="Path to a Lipseys CSV feed.")
    new_import.add_argument(
        "--davidsons-inventory-csv",
        type=Path,
        help="Path to a Davidsons inventory CSV feed.",
    )
    new_import.add_argument(
        "--davidsons-quantity-csv",
        type=Path,
        help="Optional path to a Davidsons quantity CSV feed.",
    )
    new_import.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Folder where generated GoDaddy CSV batch files will be written.",
    )
    new_import.add_argument(
        "--filename-prefix",
        default="godaddy-import",
        help="Generated CSV filename prefix.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "new-import":
        result = run_new_import_workflow(
            NewImportInput(
                lipseys_csv=args.lipseys_csv,
                davidsons_inventory_csv=args.davidsons_inventory_csv,
                davidsons_quantity_csv=args.davidsons_quantity_csv,
                output_dir=args.output_dir,
            ),
            filename_prefix=args.filename_prefix,
        )

        for message in result.messages:
            print(f"{message.severity.value.upper()}: {message.code}: {message.message}")

        if result.export_result is not None:
            print(
                "Parsed "
                f"{result.source_offers_parsed} offers from {result.source_rows_seen} rows; "
                f"exported {result.products_exported} products."
            )
            for exported_file in result.export_result.files:
                print(f"Wrote {exported_file.row_count} rows to {exported_file.path}")

        return 1 if result.has_errors else 0

    print("Inventory Feed Tool is ready.")
    return 0
