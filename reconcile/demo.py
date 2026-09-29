"""Small auditable synthetic benchmark; scenario labels never enter the matcher."""

import csv
import io
from .engine import SCHEMAS


def demo():
    bank = []
    invoices = []
    journal = []
    truth = []

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
    for row in bank:
        status = (
            "MATCHED"
            if int(row["id"][1:]) <= 43 or row["id"] == "B052"
            else ("UNALLOCATED" if row["id"] in ("B050", "B051") else "REVIEW")
        )
        truth.append(dict(bank_id=row["id"], expected_status=status))
    result = {}
    for kind, rows in zip(SCHEMAS, (bank, invoices, journal)):
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=SCHEMAS[kind])
        w.writeheader()
        w.writerows(rows)
        result[kind] = out.getvalue()
    return result, truth
