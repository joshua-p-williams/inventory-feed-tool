from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from inventory_feed_tool.cli import main


class CliTests(unittest.TestCase):
    def test_main_prints_ready_message(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("Inventory Feed Tool is ready.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
