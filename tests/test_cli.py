import contextlib
import csv
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from reconcile.__main__ import main

DEMO_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                main(list(args))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def copy_demo_inputs(self):
        folder = self.tmp / "input"
        folder.mkdir()
        for name in ("bank", "invoices", "journal"):
            shutil.copy(DEMO_DIR / f"{name}.csv", folder / f"{name}.csv")
        return folder

    def test_demo_writes_report_settlements_and_benchmark(self):
        out_dir = self.tmp / "out"
        code, stdout, _ = self.run_cli("--demo", "--output", str(out_dir))
        self.assertEqual(code, 0)
        report = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
        summary = json.loads(stdout)
        self.assertEqual(summary["run_id"], report["run_id"])
        self.assertEqual(summary["counts"], report["counts"])
        benchmark = json.loads((out_dir / "benchmark.json").read_text())
        self.assertEqual(benchmark["records"], benchmark["correct"])
        rows = list(csv.DictReader(io.StringIO(
            (out_dir / "settlements.csv").read_text(encoding="utf-8")
        )))
        self.assertTrue(rows)

    def test_demo_report_matches_committed_artifact(self):
        out_dir = self.tmp / "out"
        self.run_cli("--demo", "--output", str(out_dir))
        committed = Path(__file__).resolve().parent.parent / "artifacts" / "report.json"
        self.assertEqual(
            json.loads((out_dir / "report.json").read_text(encoding="utf-8")),
            json.loads(committed.read_text(encoding="utf-8")),
        )

    def test_input_folder_skips_benchmark(self):
        out_dir = self.tmp / "out"
        code, _, _ = self.run_cli(
            "--input", str(self.copy_demo_inputs()), "--output", str(out_dir)
        )
        self.assertEqual(code, 0)
        self.assertTrue((out_dir / "report.json").is_file())
        self.assertTrue((out_dir / "settlements.csv").is_file())
        self.assertFalse((out_dir / "benchmark.json").exists())

    def test_requires_demo_or_input(self):
        code, _, err = self.run_cli("--output", str(self.tmp / "out"))
        self.assertEqual(code, 2)
        self.assertIn("Choose --demo or --input", err)

    def test_missing_directory_is_clean_error(self):
        code, _, err = self.run_cli("--input", str(self.tmp / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("Input directory not found", err)
        self.assertNotIn("Traceback", err)

    def test_missing_files_are_listed(self):
        folder = self.copy_demo_inputs()
        (folder / "journal.csv").unlink()
        code, _, err = self.run_cli("--input", str(folder))
        self.assertEqual(code, 2)
        self.assertIn("journal.csv", err)
        self.assertNotIn("bank.csv", err)

    def test_invalid_csv_is_clean_error(self):
        folder = self.copy_demo_inputs()
        (folder / "bank.csv").write_text("wrong,columns\n1,2\n", encoding="utf-8")
        code, _, err = self.run_cli("--input", str(folder), "--output", str(self.tmp / "o"))
        self.assertEqual(code, 2)
        self.assertIn("bank: expected columns", err)
        self.assertFalse((self.tmp / "o").exists())

    def test_non_utf8_input_is_clean_error(self):
        folder = self.copy_demo_inputs()
        (folder / "invoices.csv").write_bytes(b"\xff\xfe\x00bad")
        code, _, err = self.run_cli("--input", str(folder))
        self.assertEqual(code, 2)
        self.assertIn("UTF-8", err)

    def test_out_of_range_policy_is_clean_error(self):
        code, _, err = self.run_cli("--demo", "--days", "999", "--output", str(self.tmp / "o"))
        self.assertEqual(code, 2)
        self.assertIn("days must be 0..365", err)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
