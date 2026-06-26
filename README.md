# 🧳 Tour Expense Splitter

**`trex`** — A lightweight CLI tool to track group trip expenses, split by person, and auto-calculate who owes whom.

## Install

```bash
pip install trex-expense-splitter
```

## Quick Start

```bash
# Start a trip with friends
trex trip start "Sajek Tour" --people "Hasib,Rafiq,Sumon"

# Log expenses
trex exp add 3000 --desc "Bus tickets" --paid Hasib
trex exp add 2500 --desc "Hotel room" --paid Rafiq
trex exp add 1200 --desc "Dinner" --paid Sumon

# See who owes whom
trex summary

# Close the trip
trex trip end
```

## Features

- **Equal split by default** — auto-divides among everyone on the trip
- **Partial splits** (`--for "PersonA,PersonB"`) — only split among specific people
- **Custom splits** (`--split custom`) — assign exact amounts per person
- **Mid-trip joiners** (`--joined YYYY-MM-DD`) — late joiners auto-excluded from earlier expenses
- **Persistent SQLite DB** — data survives across sessions, trips never lost
- **Multi-trip** — track multiple trips simultaneously
- **Settlement engine** — greedy algorithm minimizes payments
- **Export** — CSV and JSON formats

## How It Works

| Command | What it does |
|---|---|
| `trex trip start "Name" --people "A,B,C"` | Create a trip |
| `trex exp add AMOUNT --paid PERSON --desc WHAT` | Log an expense (equal split) |
| `trex exp add AMOUNT --paid PERSON --for "A,B"` | Split only among A & B |
| `trex summary` | Full breakdown + settlement |
| `trex trip end` | Close trip, show final settlement |
| `trex trip people add PERSON --joined DATE` | Add a late joiner |
| `trex export --format csv` | Export expenses |

## License

MIT
