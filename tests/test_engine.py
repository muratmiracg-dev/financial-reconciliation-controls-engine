import csv
import io
import unittest
from reconcile.demo import demo
from reconcile.engine import reconcile, parse_csv, money, export_csv


def edit(text, **changes):
    rows = list(csv.DictReader(io.StringIO(text)))
    for k, v in changes.items():
        rows[0][k] = v
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=rows[0])
    w.writeheader()
    w.writerows(rows)
    return out.getvalue()


def edit_record(text, record_id, **changes):
    rows = list(csv.DictReader(io.StringIO(text)))
    row = next(row for row in rows if row["id"] == record_id)
    row.update(changes)
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=rows[0])
    w.writeheader()
    w.writerows(rows)
    return out.getvalue()


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.d, self.truth = demo()

    def run_engine(self):
        return reconcile(**{k + "_csv": v for k, v in self.d.items()})

    def test_fixture_truth(self):
        r = self.run_engine()
        actual = {b: g["status"] for g in r["groups"] for b in g["bank_ids"]}
        for t in self.truth:
            self.assertEqual(
                actual.get(t["bank_id"], "UNALLOCATED"), t["expected_status"], t
            )

    def test_no_record_reuse(self):
        r = self.run_engine()
        for k in ("bank_ids", "invoice_ids"):
            ids = [x for g in r["groups"] for x in g[k]]
            self.assertEqual(len(ids), len(set(ids)))

    def test_determinism(self):
        self.assertEqual(self.run_engine(), self.run_engine())

    def test_split_batch(self):
        shapes = [
            g["shape"] for g in self.run_engine()["groups"] if g["status"] == "MATCHED"
        ]
        self.assertIn("2:1", shapes)
        self.assertIn("1:2", shapes)

    def test_fees_review(self):
        g = next(g for g in self.run_engine()["groups"] if "B044" in g["bank_ids"])
        self.assertIn("FEE_EXPLAINS_DIFFERENCE", g["flags"])
        self.assertEqual(g["status"], "REVIEW")

    def test_detached_fee_never_explains_difference(self):
        self.d["journal"] = edit_record(
            self.d["journal"], "B044C", entry_id="DETACHED"
        )
        g = next(g for g in self.run_engine()["groups"] if "B044" in g["bank_ids"])
        self.assertNotIn("FEE_EXPLAINS_DIFFERENCE", g["flags"])
        self.assertIn("LEDGER_MISMATCH", g["flags"])

    def test_currency_never_net(self):
        self.d["bank"] = edit(self.d["bank"], currency="EUR")
        g = self.run_engine()["groups"][0]
        self.assertIsNone(g["difference"])
        self.assertIn("CURRENCY_CONFLICT", g["flags"])

    def test_party_conflict(self):
        self.d["bank"] = edit(self.d["bank"], party="OTHER")
        self.assertIn("PARTY_CONFLICT", self.run_engine()["groups"][0]["flags"])

    def test_date_window(self):
        self.d["bank"] = edit(self.d["bank"], date="2025-01-01")
        self.assertIn("DATE_WINDOW", self.run_engine()["groups"][0]["flags"])

    def test_invalid_money(self):
        for x in ("NaN", "Infinity", "1.001", "bad", "1000000000001"):
            with self.assertRaises(ValueError):
                money(x)

    def test_cents_exact(self):
        self.assertEqual(money("0.29"), 29)

    def test_zero_value_journal_line_rejected(self):
        journal = edit_record(self.d["journal"], "B001A", debit="0", credit="0")
        with self.assertRaisesRegex(ValueError, "exactly one positive"):
            parse_csv(journal, "journal")

    def test_invalid_date(self):
        with self.assertRaises(ValueError):
            parse_csv(edit(self.d["bank"], date="2026-02-30"), "bank")

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            parse_csv(self.d["bank"] + self.d["bank"].splitlines()[1] + "\n", "bank")

    def test_bad_schema(self):
        with self.assertRaises(ValueError):
            parse_csv("id,date\na,b", "bank")

    def test_unbalanced_ledger_blocks_match(self):
        self.d["journal"] = edit(self.d["journal"], debit="1124")
        r = self.run_engine()
        self.assertIn("UNBALANCED_ENTRY", [i["code"] for i in r["issues"]])
        self.assertEqual(r["groups"][0]["status"], "REVIEW")

    def test_cross_date_journal_entry_blocks_match(self):
        rows = list(csv.DictReader(io.StringIO(self.d["journal"])))
        entry_id = rows[0]["entry_id"]
        linked = [row for row in rows if row["entry_id"] == entry_id]
        self.assertGreaterEqual(len(linked), 2)
        self.d["journal"] = edit_record(
            self.d["journal"], linked[-1]["id"], date="2026-08-31"
        )
        result = self.run_engine()
        conflict = next(
            issue for issue in result["issues"] if issue["code"] == "ENTRY_DATE_CONFLICT"
        )
        self.assertEqual(set(conflict["ids"]), {row["id"] for row in linked})
        group = next(group for group in result["groups"] if rows[0]["bank_id"] in group["bank_ids"])
        self.assertEqual(group["status"], "REVIEW")
        self.assertIn("LEDGER_MISMATCH", group["flags"])

    def test_missing_reference_review_only(self):
        g = next(g for g in self.run_engine()["groups"] if "B049" in g["bank_ids"])
        self.assertEqual(g["status"], "REVIEW")

    def test_ambiguity_not_allocated(self):
        self.assertNotIn(
            "B050", [b for g in self.run_engine()["groups"] for b in g["bank_ids"]]
        )

    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            reconcile(
                self.d["bank"], self.d["invoices"], self.d["journal"], tolerance=-1
            )

    def test_unknown_reference(self):
        self.d["bank"] = edit(self.d["bank"], reference="NO-SUCH-INVOICE")
        g = self.run_engine()["groups"][0]
        self.assertIn("UNKNOWN_REFERENCE", g["flags"])

    def test_csv_injection(self):
        r = self.run_engine()
        r["groups"][0]["party"] = "=1+1"
        self.assertIn("'=1+1", export_csv(r))

    def test_empty_valid_files(self):
        d = {k: v.splitlines()[0] + "\n" for k, v in self.d.items()}
        r = reconcile(d["bank"], d["invoices"], d["journal"])
        self.assertEqual(r["groups"], [])

    def test_amount_tolerance(self):
        self.d["invoices"] = edit(self.d["invoices"], amount="1125.01")
        self.assertEqual(self.run_engine()["groups"][0]["status"], "MATCHED")

    def test_negative_payment(self):
        g = next(g for g in self.run_engine()["groups"] if "B052" in g["bank_ids"])
        self.assertEqual(g["status"], "MATCHED")
        self.assertLess(g["bank_amount"], 0)


if __name__ == "__main__":
    unittest.main()
