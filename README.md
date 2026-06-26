# 🧳 Tour Expense Splitter

**`trex`** — Tracks group trip expenses, splits them among people, and auto-calculates who owes whom.

```bash
pip install trex-expense-splitter
trex trip start "Sajek Tour" --people "Tanvir,Nabila,Fahim"
trex exp add 3600 --desc "Bus tickets" --paid Tanvir
trex summary
```

---

## Table of Contents

- [Quick Start](#quick-start)
- [Full Command Reference](#full-command-reference)
- [Expense Splitting](#expense-splitting)
- [People Management](#people-management)
- [Reporting & Settlement](#reporting--settlement)
- [Data Export](#data-export)
- [Tips & Best Practices](#tips--best-practices)
- [Use Cases](#use-cases)

---

## Quick Start

```bash
# 1. Install
pip install trex-expense-splitter

# 2. Start a trip with participants
trex trip start "Cox's Bazar Trip" --dest "Cox's Bazar" --currency BDT --people "Tanvir,Nabila,Fahim"

# 3. Log expenses
trex exp add 3600 --desc "Bus ticket" --cat "Transport" --paid Tanvir
trex exp add 4500 --desc "Hotel room" --cat "Accommodation" --paid Nabila
trex exp add 1800 --desc "Dinner" --cat "Food" --paid Fahim
trex exp add 900 --desc "Breakfast" --paid Tanvir --for "Tanvir,Nabila"

# 4. View settlement
trex summary

# 5. Close trip
trex trip end
```

**Output of `trex summary`:**

```
💰 Net Balances
  Person   Paid       Owes        Balance
  Tanvir   ৳4,500    ৳3,750      +৳750
  Nabila   ৳4,500    ৳3,750      +৳750
  Fahim    ৳1,800    ৳3,300      -৳1,500

🤝 Settle Up
  Fahim → Tanvir   ৳750
  Fahim → Nabila   ৳750
```

---

## Full Command Reference

### `trex trip` — Manage Trips

| Command | Description |
|---|---|
| `trex trip start "Name" --dest "Place" --people "A,B"` | Start a new trip |
| `trex trip end [TRIP_ID]` | Close a trip + show settlement |
| `trex trip list` | List all trips |
| `trex trip list --all` | Include closed trips |
| `trex trip people add "Name"` | Add participant |
| `trex trip people add "Name" --joined 2026-06-05` | Add mid-trip joiner |
| `trex trip people remove "Name"` | Remove participant |
| `trex trip people list` | List all participants |

### `trex exp` — Manage Expenses

| Command | Description |
|---|---|
| `trex exp add AMOUNT --paid PERSON` | Add expense (equal split, all present) |
| `trex exp add AMOUNT --paid PERSON --desc "Lunch"` | Add with description |
| `trex exp add AMOUNT --paid PERSON --cat "Transport"` | Specify category |
| `trex exp add AMOUNT --paid PERSON -D 2026-06-01` | Set date |
| `trex exp add AMOUNT --paid PERSON --for "A,B"` | Split only among A and B |
| `trex exp add AMOUNT --paid PERSON --split custom` | Interactive custom split |
| `trex exp list [-t TRIP_ID]` | List expenses |
| `trex exp shares EXPENSE_ID` | Show who owes what for an expense |
| `trex exp delete EXPENSE_ID` | Remove an expense |
| `trex exp search KEYWORD` | Search expenses by keyword |

### `trex summary` — Reports

| Command | Description |
|---|---|
| `trex summary [TRIP_ID]` | Full breakdown + settlement |
| `trex cats` | List expense categories |
| `trex export [--format csv\|json]` | Export expenses |
| `trex export --format csv --output trip.csv` | Export to file |

---

## Expense Splitting

### Equal Split (default)

Every expense is split equally among all participants who were on the trip at that date. No extra flags needed:

```bash
trex exp add 3600 --desc "Bus ticket" --paid Tanvir
# Tanvir: 1200 | Nabila: 1200 | Fahim: 1200
```

### Partial Split (`--for`)

When only some people share an expense, use `--for`:

```bash
# Only Tanvir and Nabila ate breakfast
trex exp add 900 --desc "Breakfast" --paid Tanvir --for "Tanvir,Nabila"
# Tanvir: 450 | Nabila: 450 | Fahim: 0
```

People not in `--for` get a zero share. No manual calculation needed.

### Custom Split (`--split custom`)

When you need exact amounts per person:

```bash
trex exp add 2500 --desc "Shopping" --paid Fahim --split custom
# Prompts for each person's share:
#   Tanvir: 1000
#   Nabila: 1000
#   Fahim: 500 (auto-calculated)
```

You can also pipe amounts:
```bash
printf "1000\n1000\n500\n" | trex exp add 2500 --desc "Shopping" --paid Fahim --split custom
```

### Rounding

`trex` handles rounding intelligently. When equal splits don't divide evenly, the last person in the list gets the remaining fraction so the total always matches:

```bash
trex exp add 100 --desc "Tea" --paid Tanvir --for "Tanvir,Nabila,Fahim"
# Tanvir: 33.34 | Nabila: 33.33 | Fahim: 33.33
# Total: 100.00 ✓
```

---

## People Management

### Mid-Trip Joiners (`--joined`)

When someone joins the trip late, add them with their join date. Expenses before that date auto-exclude them:

```bash
# Day 1 — only Tanvir and Nabila
trex trip start "Sajek Tour" --people "Tanvir,Nabila"
trex exp add 2000 --desc "Bus" --paid Tanvir -D "2026-06-01"
# Split: Tanvir 1000, Nabila 1000

# Day 2 — Fahim joins
trex trip people add "Fahim" --joined "2026-06-02"
trex exp add 3000 --desc "Cottage" --paid Nabila -D "2026-06-02"
# Split: Tanvir 1000, Nabila 1000, Fahim 1000

trex exp add 900 --desc "Breakfast" --paid Tanvir -D "2026-06-03"
# Split: Tanvir 300, Nabila 300, Fahim 300
```

### Changing Participants

```bash
# Remove someone who left the trip early
trex trip people remove "Rafiq"

# See who's on the trip
trex trip people list
```

---

## Reporting & Settlement

### The Settlement Algorithm

1. **Each person's total paid** — sum of all expenses they fronted
2. **Each person's total owed** — sum of their shares across all expenses
3. **Net balance** = paid − owed
   - Positive → they're a **creditor** (owed money)
   - Negative → they're a **debtor** (owes money)
4. **Greedy settlement** — pairs largest creditor with largest debtor, minimizes number of payments

### Reading a Summary

```
💰 Net Balances
  Person   Paid       Owes       Balance
  Tanvir   ৳4,500    ৳3,750     +৳750    ← owed 750
  Nabila   ৳4,500    ৳3,750     +৳750    ← owed 750
  Fahim    ৳1,800    ৳3,300     -৳1,500  ← owes 1500

🤝 Settle Up
  Fahim → Tanvir   ৳750    ← Fahim pays Tanvir 750
  Fahim → Nabila   ৳750    ← Fahim pays Nabila 750
```

---

## Data Export

```bash
# CSV
trex export --format csv
trex export --format csv --output sajek-trip.csv

# JSON (includes per-person shares)
trex export --format json
trex export --format json --output sajek-trip.json
```

JSON output includes full split details:
```json
{
  "date": "2026-06-01",
  "category": "Transport",
  "amount": 3600,
  "currency": "BDT",
  "paid_by": "Tanvir",
  "description": "Bus (Dhaka → Sajek)",
  "shares": [
    {"name": "Tanvir", "amount": 1200},
    {"name": "Nabila", "amount": 1200},
    {"name": "Fahim", "amount": 1200}
  ]
}
```

---

## Tips & Best Practices

- **Currency is locked per trip** — set at `trip start` with `--currency` (e.g. `--currency USD`, `--currency BDT`, `--currency MYR`). All expenses and settlements use that currency. To track a trip in a different currency, start a new trip.
- **Categories are auto-detected** — use `trex cats` to see all 8 default categories
- **The DB is at `~/.tourexpenses/expenses.db`** — delete it to start fresh
- **Add participants BEFORE expenses** that should include them
- **Dates are YYYY-MM-DD** — always use this format
- **`--for` uses comma-separated names** without spaces: `--for "Tanvir,Nabila"`

---

## Use Cases

### Short Weekend Trip
```bash
trex trip start "Dhaka Weekend" --people "Tanvir,Nabila,Fahim"
trex exp add 2400 --desc "Movie tickets" --paid Tanvir
trex exp add 1200 --desc "Lunch" --paid Nabila
trex exp add 600 --desc "Rickshaw" --paid Fahim
trex summary
trex trip end
```

### Long Tour with Mid-Trip Joiners
```bash
trex trip start "Sajek 5 Days" --dest "Sajek" --people "Tanvir,Nabila"
# Day 1-2: just the two of them
trex exp add 3000 --desc "Bus tickets" --paid Tanvir -D "2026-06-01"
trex exp add 2500 --desc "Hotel night 1" --paid Nabila -D "2026-06-01"
# Fahim joins day 3
trex trip people add "Fahim" --joined "2026-06-03"
trex exp add 2500 --desc "Hotel night 2" --paid Nabila -D "2026-06-03"
trex exp add 1500 --desc "Dinner all 3" --paid Fahim -D "2026-06-03"
# Only Tanvir and Fahim go for a hike
trex exp add 800 --desc "Guide fee" --paid Tanvir -D "2026-06-04" --for "Tanvir,Fahim"
trex summary
```

### International Trip
```bash
trex trip start "Bangkok 2026" --dest "Bangkok" --currency THB --people "Tanvir,Nabila"
trex exp add 4500 --desc "Flight BKK-DHK" --paid Tanvir
trex exp add 3000 --desc "Hotel 2 nights" --paid Nabila
trex summary
trex export --format json --output bangkok.json
```
