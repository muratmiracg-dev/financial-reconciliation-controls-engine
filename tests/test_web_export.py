"""Browser CSV export must neutralise spreadsheet formulas exactly like export_csv."""

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from reconcile.demo import demo
from reconcile.engine import reconcile

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

# Load only the top-level csvCell function from web/app.js into a fresh V8 context.
RUNNER = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync(process.argv[1], "utf8");
const match = src.match(/^function csvCell\(v\) \{[\s\S]*?^\}$/m);
if (!match) { console.error("csvCell not found"); process.exit(2); }
const ctx = {}; vm.runInNewContext(match[0] + "; this.csvCell = csvCell;", ctx);
const values = JSON.parse(fs.readFileSync(0, "utf8"));
process.stdout.write(JSON.stringify(values.map((v) => ctx.csvCell(v))));
"""


@unittest.skipIf(NODE is None, "node is required for the browser export test")
class BrowserCsvCellTests(unittest.TestCase):
    def cells(self, values):
        result = subprocess.run(
            [NODE, "-e", RUNNER, str(ROOT / "web" / "app.js")],
            input=json.dumps(values),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_formula_prefixes_are_neutralised_in_strings_and_id_lists(self):
        values = ["=1+1", " +SUM(A1)", "@cmd", "-text", ["INV-1", "=HYPERLINK(\"x\")"], ["=1+1"]]
        self.assertEqual(
            self.cells(values),
            ['"\'=1+1"', '"\' +SUM(A1)"', '"\'@cmd"', '"\'-text"',
             '"INV-1;=HYPERLINK(""x"")"', '"\'=1+1"'],
        )

    def test_numbers_and_safe_values_are_unchanged(self):
        self.assertEqual(
            self.cells([-125, 0, 112500, "INV-001", ["B001", "B002"], None, 'say "hi"']),
            ['"-125"', '"0"', '"112500"', '"INV-001"', '"B001;B002"', '""', '"say ""hi"""'],
        )

    def test_matches_python_export_for_formula_invoice_id(self):
        data, _ = demo()
        tampered = {name: text.replace("INV-001", "=1+1") for name, text in data.items()}
        result = reconcile(tampered["bank"], tampered["invoices"], tampered["journal"])
        group = next(g for g in result["groups"] if "=1+1" in g["invoice_ids"])
        self.assertEqual(self.cells([group["invoice_ids"]]), ['"\'=1+1"'])


if __name__ == "__main__":
    unittest.main()
