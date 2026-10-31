import argparse
import json
from pathlib import Path
from .demo import demo
from .engine import reconcile, export_csv


INPUT_FILES = ("bank", "invoices", "journal")


def _read_inputs(folder):
    if not folder.is_dir():
        raise ValueError(f"Input directory not found: {folder}")
    missing = [f"{k}.csv" for k in INPUT_FILES if not (folder / f"{k}.csv").is_file()]
    if missing:
        raise ValueError(f"Missing input file(s) in {folder}: {', '.join(missing)}")
    try:
        return {
            k: (folder / f"{k}.csv").read_text(encoding="utf-8-sig")
            for k in INPUT_FILES
        }
    except UnicodeDecodeError as exc:
        raise ValueError(f"Input files must be UTF-8 encoded CSV: {exc.reason}") from exc


def main(argv=None):
    p = argparse.ArgumentParser(description="Local financial reconciliation")
    p.add_argument("--demo", action="store_true")
    p.add_argument("--input", type=Path)
    p.add_argument("--output", type=Path, default=Path("output"))
    p.add_argument("--days", type=int, default=45)
    p.add_argument("--tolerance", type=int, default=1)
    args = p.parse_args(argv)
    if not args.demo and args.input is None:
        p.error("Choose --demo or --input DIRECTORY")
    try:
        data, truth = (
            demo() if args.demo else (_read_inputs(args.input), None)
        )
        result = reconcile(
            data["bank"], data["invoices"], data["journal"], args.days, args.tolerance
        )
    except (ValueError, TypeError) as exc:
        p.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    (args.output / "settlements.csv").write_text(export_csv(result), encoding="utf-8")
    if truth:
        predicted = {
            bid: g["status"] for g in result["groups"] for bid in g["bank_ids"]
        }
        correct = sum(
            predicted.get(t["bank_id"], "UNALLOCATED") == t["expected_status"]
            for t in truth
        )
        (args.output / "benchmark.json").write_text(
            json.dumps(
                dict(
                    records=len(truth),
                    correct=correct,
                    note="Controlled fixture agreement; not real-world accuracy",
                ),
                indent=2,
            )
        )
    print(
        json.dumps(
            dict(
                run_id=result["run_id"],
                counts=result["counts"],
                summary=result["summary"],
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
