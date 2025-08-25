# logic.py
from decimal import Decimal, ROUND_HALF_UP

def _to_cents(x) -> int:
    d = Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(d * 100)

def _from_cents(cents: int) -> float:
    return float(Decimal(cents) / Decimal(100))

def calculate_balances(people_names: list[str], expenses: list[dict]):
    """Return dict person->balance (positive means should receive)."""
    balances_cents = {p: 0 for p in people_names}

    for exp in expenses:
        participants = [p for p in exp.get("participants", []) if p in balances_cents]
        if not participants:
            continue

        amount_cents = _to_cents(exp["amount"])
        payer = exp["paid_by"]
        if payer in balances_cents:
            balances_cents[payer] += amount_cents

        n = len(participants)
        per = amount_cents // n
        remainder = amount_cents - per * n  # distribute extra cents fairly

        for i, person in enumerate(participants):
            share = per + (1 if i < remainder else 0)
            balances_cents[person] -= share

    return {p: round(_from_cents(c), 2) for p, c in balances_cents.items()}

def calculate_settlements(balances: dict[str, float]):
    cents = {p: _to_cents(v) for p, v in balances.items()}
    creditors = [(p, a) for p, a in cents.items() if a > 1]
    debtors   = [(p, a) for p, a in cents.items() if a < -1]

    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1])

    settlements = []
    i = j = 0
    while i < len(creditors) and j < len(debtors):
        cp, ca = creditors[i]
        dp, da = debtors[j]

        amt = min(ca, -da)
        if amt > 1:
            settlements.append({
                "from": dp,
                "to": cp,
                "amount": round(_from_cents(amt), 2)
            })

        ca -= amt
        da += amt

        if ca <= 1:  i += 1
        else:        creditors[i] = (cp, ca)

        if da >= -1: j += 1
        else:        debtors[j]   = (dp, da)

    return settlements
