from __future__ import annotations

import argparse

from inventory_feed_tool import __version__


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    print("Inventory Feed Tool is ready.")
    return 0
