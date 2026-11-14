"""Small auditable synthetic benchmark; scenario labels never enter the matcher."""

import csv
import io
from .engine import SCHEMAS


def demo():
    bank = []
    invoices = []
    journal = []
    truth = []
    intended = {}

    def inv(i, amount, party=None, description="Consulting services"):
        invoices.append(
            dict(
                id=i,
                date="2026-09-01",
                party=party or i,
                currency="TRY",
                amount=str(amount),
                description=description,
            )
        )

    def pay(
        b, amount, refs, party, ledger=True, fee=0, description="Consulting services"
    ):
        # The invoices a payment settles, recorded for scoring only (never passed to
        # the matcher). Unreferenced payments get their intended invoice set below.
        intended[b] = sorted(x for x in refs.split(";") if x)
        bank.append(
            dict(
                id=b,
                date="2026-09-05",
                party=party,
                currency="TRY",
                amount=str(amount),
                reference=refs,
                description=description,
            )
        )
        if ledger:
            for suffix, account, debit, credit in [
                ("A", "BANK", max(amount, 0), max(-amount, 0)),
                ("B", "AR", max(-amount - fee, 0), max(amount + fee, 0)),
            ] + ([("C", "FEE", fee, 0)] if fee else []):
                journal.append(
                    dict(
                        id=b + suffix,
                        entry_id="E" + b,
                        date="2026-09-05",
                        bank_id=b,
                        account=account,
                        currency="TRY",
                        debit=str(debit),
                        credit=str(credit),
                    )
                )

    for n in range(1, 41):
        i = f"INV-{n:03}"
        amount = 1000 + n * 125
        inv(i, amount)
        pay(f"B{n:03}", amount, i, i)
    inv("SPLIT", 12000)
    pay("B041", 5000, "SPLIT", "SPLIT")
    pay("B042", 7000, "SPLIT", "SPLIT")
    inv("BATCH-A", 4000, "BATCH")
    inv("BATCH-B", 6000, "BATCH")
    pay("B043", 10000, "BATCH-A;BATCH-B", "BATCH")
    inv("FEE", 10000)
    pay("B044", 9975, "FEE", "FEE", fee=25)
    inv("PARTIAL", 8000)
    pay("B045", 3000, "PARTIAL", "PARTIAL")
    inv("DUP", 4500)
    pay("B046", 4500, "DUP", "DUP")
    pay("B047", 4500, "DUP", "DUP")
    inv("MISSING-GL", 2500)
    pay("B048", 2500, "MISSING-GL", "MISSING-GL", ledger=False)
    inv("UNREFERENCED", 3750)
    pay("B049", 3750, "", "UNREFERENCED")
    inv("AMB-A", 1700, "AMB", description="Order A")
    inv("AMB-B", 1700, "AMB", description="Order B")
    pay("B050", 1700, "", "AMB")
    inv("OPEN", 5200)
    pay("B051", 990, "", "UNKNOWN")
    inv("OUTFLOW", -2100)
    pay("B052", -2100, "OUTFLOW", "OUTFLOW")
    inv("OVERPAY", 2000)
    pay("B053", 2200, "OVERPAY", "OVERPAY")
    # B049 has no reference but a unique amount/date/party candidate, which is the
    # invoice it pays. B050 is ambiguous and B051 has no candidate: no allocation.
    intended["B049"] = ["UNREFERENCED"]
    for row in bank:
        status = (
            "MATCHED"
            if int(row["id"][1:]) <= 43 or row["id"] == "B052"
            else ("UNALLOCATED" if row["id"] in ("B050", "B051") else "REVIEW")
        )
        truth.append(
            dict(
                bank_id=row["id"],
                expected_status=status,
                expected_invoice_ids=intended[row["id"]] if status != "UNALLOCATED" else [],
            )
        )
    result = {}
    for kind, rows in zip(SCHEMAS, (bank, invoices, journal)):
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=SCHEMAS[kind])
        w.writeheader()
        w.writerows(rows)
        result[kind] = out.getvalue()
    return result, truth


def score_benchmark(result, truth):
    """Compare engine output with fixture truth on status AND invoice allocation.

    A bank record counts as correct only when its status matches and it is grouped
    with exactly the expected invoices, so a payment allocated to the wrong invoice
    can no longer pass as a correct MATCHED or REVIEW result.
    """

    by_bank = {bid: g for g in result["groups"] for bid in g["bank_ids"]}
    status_ok = allocation_ok = correct = 0
    mismatches = []
    for t in truth:
        group = by_bank.get(t["bank_id"])
        status = group["status"] if group else "UNALLOCATED"
        invoice_ids = sorted(group["invoice_ids"]) if group else []
        s_ok = status == t["expected_status"]
        a_ok = invoice_ids == sorted(t["expected_invoice_ids"])
        status_ok += s_ok
        allocation_ok += a_ok
        correct += s_ok and a_ok
        if not (s_ok and a_ok):
            mismatches.append(
                dict(
                    bank_id=t["bank_id"],
                    expected_status=t["expected_status"],
                    status=status,
                    expected_invoice_ids=sorted(t["expected_invoice_ids"]),
                    invoice_ids=invoice_ids,
                )
            )
    return dict(
        records=len(truth),
        status_correct=status_ok,
        allocation_correct=allocation_ok,
        correct=correct,
        mismatches=mismatches,
        note="Controlled fixture agreement on status and invoice allocation; "
        "not real-world accuracy",
    )
