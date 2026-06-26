# 🧳 Tour Expense Splitter — Complete Demo

This walkthrough shows **every feature** using a realistic 4-day trip. You can copy-paste each command or tell your AI assistant the natural language prompts.

---

## Trip: Sajek Valley (4 Days, 3 People)

**Participants:** Tanvir, Nabila, Fahim
**Currency:** BDT (Bangladeshi Taka)

---

### Part 1: Setup & First Day

**👉 Start the trip**

```
Natural: "Start a trip called Sajek Valley with Tanvir, Nabila, and Fahim"
CLI:     trex trip start "Sajek Valley" --dest "Sajek, Rangamati" --currency BDT --people "Tanvir,Nabila,Fahim"
```

**👉 Log Day 1 expenses**

| Natural language | Command |
|---|---|
| "Bus tickets 3600, Tanvir paid" | `trex exp add 3600 --desc "Bus Dhaka→Sajek" --cat Transport --paid Tanvir -D 2026-06-01` |
| "Cottage booking 4500, Nabila paid" | `trex exp add 4500 --desc "Cottage 2 nights" --cat Accommodation --paid Nabila -D 2026-06-01` |
| "Dinner 1800, Fahim paid" | `trex exp add 1800 --desc "Dinner at restaurant" --cat Food --paid Fahim -D 2026-06-01` |

**What happened:** Each expense was split equally 3 ways automatically.

```
🚕 3,600 Bus → Tanvir: 1,200 | Nabila: 1,200 | Fahim: 1,200
🏨 4,500 Cottage → Tanvir: 1,500 | Nabila: 1,500 | Fahim: 1,500
🍽️ 1,800 Dinner → Tanvir: 600 | Nabila: 600 | Fahim: 600
```

---

### Part 2: Partial Split (Not Everyone Pays)

**👉 Day 2 — Only Tanvir and Nabila had breakfast together. Fahim slept in.**

```
Natural: "Breakfast 900, Tanvir paid, just for Tanvir and Nabila"
CLI:     trex exp add 900 --desc "Breakfast" --cat Food --paid Tanvir -D 2026-06-02 --for "Tanvir,Nabila"
```

**Result:** 450 each for Tanvir & Nabila. Fahim gets 0 share.

```
🍽️ 900 Breakfast → Tanvir: 450 | Nabila: 450 | Fahim: 0
```

---

### Part 3: Mid-Trip Joiner

**👉 Day 3 — A fourth friend Meem joins the trip.**

```
Natural: "Meem joins the trip today (June 3)"
CLI:     trex trip people add "Meem" --joined "2026-06-03"
```

**👉 Log Day 3 expenses — Meem is now included.**

| Natural language | Command |
|---|---|
| "Hotel extension 2500, Nabila paid" | `trex exp add 2500 --desc "Hotel night 3" --cat Accommodation --paid Nabila -D 2026-06-03` |
| "Lunch 2000, Fahim paid" | `trex exp add 2000 --desc "Lunch at local cafe" --cat Food --paid Fahim -D 2026-06-03` |

**Result:** These expenses split 4 ways (including Meem).

```
🏨 2,500 Hotel → Tanvir: 625 | Nabila: 625 | Fahim: 625 | Meem: 625
🍽️ 2,000 Lunch → Tanvir: 500 | Nabila: 500 | Fahim: 500 | Meem: 500
```

---

### Part 4: Custom Split

**👉 Day 4 — A souvenir where everyone bought different things.**

```
Natural: "Shopping 3000, Meem paid, custom split: Tanvir 1000, Nabila 500, Fahim 800, Meem 700"
CLI:     trex exp add 3000 --desc "Souvenir shopping" --cat Shopping --paid Meem -D 2026-06-04 --split custom
         # Then enter: 1000, 500, 800, 700
```

**Result:**
```
🛍️ 3,000 Shopping → Tanvir: 1,000 | Nabila: 500 | Fahim: 800 | Meem: 700
```

---

### Part 5: Check Mid-Trip Balance

```
Natural: "How much does everyone owe so far?"
CLI:     trex summary
```

**Output:**
```
💰 Net Balances
  Person   Paid       Owes       Balance
  Tanvir   ৳4,500    ৳4,275     +৳225
  Nabila   ৳7,000    ৳3,775     +৳3,225
  Fahim    ৳3,800    ৳4,275     -৳475
  Meem     ৳3,000    ৳2,175     +৳825

🤝 Settle Up
  Fahim → Nabila  ৳475
```

---

### Part 6: Close Trip + Final Settlement

```
Natural: "We're done, close the trip"
CLI:     trex trip end
```

**Final settlement printed automatically.**

---

### Part 7: Export Everything

```
Natural: "Export the trip data as CSV"
CLI:     trex export --format csv --output sajek-trip.csv

Natural: "Export as JSON with all the splits"
CLI:     trex export --format json --output sajek-trip.json
```

---

## Summary of All Features Used

| Feature | Example |
|---|---|
| **Basic equal split** | `trex exp add 3600 --desc "Bus" --paid Tanvir` |
| **Partial split** | `trex exp add 900 --paid Tanvir --for "Tanvir,Nabila"` |
| **Mid-trip joiner** | `trex trip people add "Meem" --joined "2026-06-03"` |
| **Custom split** | `trex exp add 3000 --paid Meem --split custom` |
| **Auto-settlement** | `trex summary` → who owes whom |
| **Export CSV** | `trex export --format csv` |
| **Export JSON** | `trex export --format json` |
| **Close trip** | `trex trip end` |

---

## For AI Assistants

When a user asks you to track trip expenses:

1. **Start a trip** when they tell you who's going
2. **Log each expense** as they tell you — ask for who paid if not specified
3. **Show confirmation** after each expense so they can catch errors
4. **Use `--for`** when they say "only X and Y shared this"
5. **Use `--joined`** when someone joins late
6. **Run `trex summary`** when they ask "who owes what"
7. **Run `trex trip end`** when the trip is over

The CLI handles all the math. You just translate natural language to commands.
