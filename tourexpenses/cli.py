"""Tour Expense Splitter CLI."""

import sys
import json
import click
from datetime import date, datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from . import db

console = Console()

CURRENCY_SYMBOLS = {
    "BDT": "৳", "USD": "$", "EUR": "€", "GBP": "£",
    "INR": "₹", "MYR": "RM", "SGD": "S$", "AUD": "A$",
}

def fmt(amount, currency="BDT"):
    sym = CURRENCY_SYMBOLS.get(currency, currency + " ")
    return f"{sym}{amount:,.2f}"


# ─── Helpers ────────────────────────────────────────────────────────────

def _pick_active_trip():
    trips = db.list_trips(include_closed=False)
    active = [t for t in trips if t["is_active"]]
    if not active:
        console.print("[red]No active trips. Start one with `trex trip start`.[/]")
        sys.exit(1)
    if len(active) == 1:
        return active[0]
    console.print("[bold]Select a trip:[/]")
    for i, t in enumerate(active, 1):
        console.print(f"  {i}. [bold]{t['name']}[/] — {t['destination'] or '—'}  ({t['currency']})")
    try:
        choice = int(click.prompt("Enter number", type=int))
        return active[choice - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid.[/]")
        sys.exit(1)


def _pick_participant(trip_id, prompt="Select person"):
    people = db.get_participants(trip_id)
    if not people:
        console.print("[red]No participants in this trip. Add some with `trex trip people add`.[/]")
        sys.exit(1)
    if len(people) == 1:
        return people[0]
    console.print(f"[bold]{prompt}:[/]")
    for i, p in enumerate(people, 1):
        console.print(f"  {i}. {p['name']}")
    try:
        choice = int(click.prompt("Enter number", type=int))
        return people[choice - 1]
    except (ValueError, IndexError):
        console.print("[red]Invalid.[/]")
        sys.exit(1)


# ─── Root ────────────────────────────────────────────────────────────────

@click.group()
@click.version_option("0.2.0")
def cli():
    """🧳 Tour Expense Splitter — track trip expenses & split by person."""
    db.init_db()


# ─── Trip Commands ──────────────────────────────────────────────────────

@cli.group()
def trip():
    """Manage trips & participants."""


@trip.command("start")
@click.argument("name")
@click.option("--dest", "-d", default="", help="Destination")
@click.option("--currency", "-c", default="BDT", help="Currency for the entire trip (BDT, USD, etc.) — cannot be changed later")
@click.option("--people", "-p", "people", default="", help="Comma-separated participant names")
def trip_start(name, dest, currency, people):
    """Start a new trip with participants.

    All expenses in this trip will use the currency specified here. Currency
    is locked to the trip for consistency in settlement calculations.
    """
    trip_id = db.create_trip(name, dest, currency.upper())
    if people:
        for p_name in [n.strip() for n in people.split(",") if n.strip()]:
            db.add_participant(trip_id, p_name)
    console.print(f"[green]✅ Trip started:[/] [bold]{name}[/] ({dest or '—'})  #{trip_id}")
    people_list = db.get_participants(trip_id)
    if people_list:
        console.print("   👥 " + ", ".join(f"{p['name']} ({p['joined_on'] or 'start'})" for p in people_list))


@trip.command("end")
@click.argument("trip_id", type=int, required=False)
def trip_end(trip_id):
    """Close a trip and show final settlement."""
    if trip_id is None:
        t = _pick_active_trip()
        trip_id = t["id"]
    t = db.get_trip(trip_id)
    if not t:
        console.print("[red]Trip not found.[/]")
        sys.exit(1)
    db.close_trip(trip_id)

    # Show settlement
    s = db.compute_settlement(trip_id)
    console.print(f"\n[green]✅ Trip closed![/] [bold]{t['name']}[/]")
    _print_settlement(s)


@trip.command("reopen")
@click.argument("trip_id", type=int)
def trip_reopen(trip_id):
    """Reopen a closed trip (undo trip end)."""
    t = db.get_trip(trip_id)
    if not t:
        console.print("[red]Trip not found.[/]")
        sys.exit(1)
    if t["is_active"]:
        console.print(f"[yellow]Trip is already active.[/]")
        return
    db.reopen_trip(trip_id)
    console.print(f"[green]✅ Trip reopened:[/] [bold]{t['name']}[/]")


@trip.command("list")
@click.option("--all", "-a", "include_closed", is_flag=True, help="Include closed trips")
def trip_list(include_closed):
    """List all trips."""
    trips = db.list_trips(include_closed=include_closed)
    if not trips:
        console.print("[yellow]No trips yet.[/]")
        return
    table = Table(title="Trips")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Destination")
    table.add_column("Currency")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Status")
    for t in trips:
        status = "[green]Active[/]" if t["is_active"] else "[dim]Closed[/]"
        table.add_row(
            str(t["id"]), t["name"], t["destination"] or "—",
            t["currency"], t["start_date"], t["end_date"] or "…", status,
        )
    console.print(table)


# ─── People Commands ────────────────────────────────────────────────────

@trip.group()
def people():
    """Manage trip participants."""


@people.command("add")
@click.argument("names", nargs=-1, required=True)
@click.option("--trip", "-t", "trip_id", type=int, default=None)
@click.option("--joined", "-j", "joined_on", default=None, help="Join date (YYYY-MM-DD), defaults to trip start")
def people_add(names, trip_id, joined_on):
    """Add participants to a trip."""
    if trip_id is None:
        t = _pick_active_trip()
        trip_id = t["id"]
    for name in names:
        db.add_participant(trip_id, name, joined_on)
    console.print(f"[green]✅ Added:[/] {', '.join(names)}")
    if joined_on:
        console.print(f"   Joined on: {joined_on}")
    people = db.get_participants(trip_id)
    console.print("   👥 " + ", ".join(f"{p['name']} ({p['joined_on'] or 'start'})" for p in people))


@people.command("remove")
@click.argument("name")
@click.option("--trip", "-t", "trip_id", type=int, default=None)
def people_remove(name, trip_id):
    """Remove a participant from a trip."""
    if trip_id is None:
        t = _pick_active_trip()
        trip_id = t["id"]
    if db.remove_participant(trip_id, name):
        console.print(f"[red]🗑️ Removed {name}[/]")
    else:
        console.print(f"[red]{name} not found in this trip.[/]")


@people.command("list")
@click.option("--trip", "-t", "trip_id", type=int, default=None)
def people_list(trip_id):
    """List participants in a trip."""
    if trip_id is None:
        t = _pick_active_trip()
        trip_id = t["id"]
    people = db.get_participants(trip_id)
    if not people:
        console.print("[yellow]No participants. Add with `trex trip people add`.[/]")
        return
    trip_name = db.get_trip(trip_id)["name"]
    table = Table(title=f"👥 {trip_name} — Participants")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Joined")
    for p in people:
        table.add_row(str(p["id"]), p["name"], p["joined_on"] or "(start)")
    console.print(table)


# ─── Expense Commands ──────────────────────────────────────────────────

@cli.group()
def exp():
    """Manage trip expenses."""


@exp.command("add")
@click.argument("amount", type=float)
@click.option("--desc", "-d", "description", default="", help="Description")
@click.option("--cat", "-c", "category_name", default="", help="Category name")
@click.option("--paid", "-p", "paid_by_name", default=None, help="Who paid (name)")
@click.option("--trip", "-t", "trip_id", type=int, default=None, help="Trip ID")
@click.option("--date", "-D", "expense_date", default=None, help="Date (YYYY-MM-DD)")
@click.option("--split", type=click.Choice(["equal", "custom"]), default="equal", help="Split method")
@click.option("--for", "-f", "split_for", default=None, help="Split only among these people (comma-sep names)")
def exp_add(amount, description, category_name, paid_by_name, trip_id, expense_date, split, split_for):
    """Add an expense split among participants."""
    # Pick trip
    if trip_id is None:
        t = _pick_active_trip()
    else:
        t = db.get_trip(trip_id)
        if not t:
            console.print("[red]Trip not found.[/]")
            sys.exit(1)
    trip_id = t["id"]

    # Pick payer
    if paid_by_name:
        people = db.get_participants(trip_id)
        match = [p for p in people if paid_by_name.lower() == p["name"].lower()]
        if not match:
            console.print(f"[red]'{paid_by_name}' not in trip participants.[/]")
            sys.exit(1)
        payer = match[0]
    else:
        payer = _pick_participant(trip_id, "Who paid?")

    # Pick category
    cats = db.list_categories()
    if category_name:
        match = [c for c in cats if category_name.lower() in c["name"].lower()]
        if not match:
            console.print(f"[red]Category '{category_name}' not found.[/]")
            sys.exit(1)
        cat = match[0]
    else:
        console.print("[bold]Category:[/]")
        for i, c in enumerate(cats, 1):
            console.print(f"  {i}. {c['emoji']} {c['name']}")
        try:
            choice = int(click.prompt("Enter number", type=int))
            cat = cats[choice - 1]
        except (ValueError, IndexError):
            console.print("[red]Invalid.[/]")
            sys.exit(1)

    # Custom split?
    custom_shares = None
    if split == "custom":
        people = db.get_participants(trip_id)
        while True:
            console.print(f"[bold]Custom split for {fmt(amount, t['currency'])}:[/]")
            console.print(f"  (Enter each person's share. Sum must equal {fmt(amount, t['currency'])})")
            custom_shares = {}
            for p in people:
                while True:
                    share = click.prompt(
                        f"  {p['name']}'s share",
                        type=float,
                    )
                    if share < 0:
                        console.print(f"[red]⚠️  Share cannot be negative. Try again.[/]")
                        continue
                    break
                share = round(share, 2)
                custom_shares[p["id"]] = share

            # Validate sum
            total_entered = round(sum(custom_shares.values()), 2)
            if abs(total_entered - amount) < 0.01:
                break  # Valid
            else:
                console.print(
                    f"[red]⚠️  Shares sum to {fmt(total_entered, t['currency'])} "
                    f"but expense is {fmt(amount, t['currency'])}.[/]"
                )
                if not click.confirm("Re-enter shares?", default=True):
                    console.print(f"[yellow]⚠️  Saved with discrepancy (sum={fmt(total_entered, t['currency'])}).[/]")
                    break

    split_for_list = split_for.split(",") if split_for else None

    try:
        eid = db.add_expense(
            trip_id=trip_id,
            category_id=cat["id"],
            amount=amount,
            paid_by=payer["id"],
            description=description or "",
            expense_date=expense_date,
            split_type=split,
            custom_shares=custom_shares,
            split_for=split_for_list,
        )
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

    console.print(f"\n[green]✅ Expense logged![/] {cat['emoji']} {fmt(amount, t['currency'])} — {description or cat['name']}")
    split_info = f"Paid by [bold]{payer['name']}[/] | Split: [bold]{split}[/]"
    if split_for:
        split_info += f" for {split_for}"
    split_info += f" | Date: {expense_date or date.today().isoformat()}"
    console.print(f"   {split_info}")

    # Show the split
    people_shares = db.get_expense_shares(eid)
    share_str = " | ".join(f"{s['name']}: {fmt(s['share_amount'], t['currency'])}" for s in people_shares)
    console.print(f"   📊 {share_str}")


@exp.command("list")
@click.option("--trip", "-t", "trip_id", type=int, default=None)
@click.option("--cat", "-c", "category_id", type=int, default=None)
@click.option("--limit", "-l", type=int, default=20)
def exp_list(trip_id, category_id, limit):
    """List expenses for a trip."""
    if trip_id is None:
        t = _pick_active_trip()
        trip_id = t["id"]
    rows = db.get_expenses(trip_id=trip_id, category_id=category_id, limit=limit)
    if not rows:
        console.print("[yellow]No expenses.[/]")
        return
    table = Table(title="Expenses")
    table.add_column("ID", style="dim")
    table.add_column("Date")
    table.add_column("Cat")
    table.add_column("Amount")
    table.add_column("Paid By")
    table.add_column("Split")
    table.add_column("Description")
    for r in rows:
        table.add_row(
            str(r["id"]),
            r["expense_date"],
            f"{r['emoji']}{r['category']}",
            fmt(r["amount"], r["currency"]),
            r["paid_by_name"],
            r["split_type"],
            r["description"][:30] or "—",
        )
    console.print(table)


@exp.command("shares")
@click.argument("expense_id", type=int)
def exp_shares(expense_id):
    """Show how an expense was split."""
    shares = db.get_expense_shares(expense_id)
    if not shares:
        console.print("[red]Expense not found or no shares.[/]")
        return
    table = Table(title=f"Expense #{expense_id} — Splits")
    table.add_column("Person")
    table.add_column("Share")
    for s in shares:
        table.add_row(s["name"], fmt(s["share_amount"]))
    console.print(table)


@exp.command("update")
@click.argument("expense_id", type=int)
@click.option("--desc", "description", default=None, help="New description")
@click.option("--date", "expense_date", default=None, help="New date (YYYY-MM-DD)")
@click.option("--cat", "category_name", default=None, help="New category name")
@click.option("--amount", type=float, default=None, help="New amount (recalculates shares)")
@click.option("--paid", "paid_by_name", default=None, help="New payer (name)")
def exp_update(expense_id, description, expense_date, category_name, amount, paid_by_name):
    """Update an expense's fields. Recalculates shares if amount changes."""
    # Validate at least one update was requested
    if description is None and expense_date is None and category_name is None and amount is None and paid_by_name is None:
        console.print("[yellow]No update fields provided. Use --help to see options.[/]")
        return

    # Resolve category
    category_id = None
    if category_name is not None:
        cats = db.list_categories()
        match = [c for c in cats if category_name.lower() in c["name"].lower()]
        if not match:
            console.print(f"[red]Category '{category_name}' not found.[/]")
            sys.exit(1)
        category_id = match[0]["id"]

    # Resolve payer
    paid_by_id = None
    if paid_by_name is not None:
        # Get the trip_id from this expense
        existing = db.get_expense_shares(expense_id)
        if not existing:
            console.print(f"[red]Expense #{expense_id} not found.[/]")
            sys.exit(1)
        trip_id = db.get_expense_trip_id(expense_id)
        people = db.get_participants(trip_id)
        match = [p for p in people if paid_by_name.lower() == p["name"].lower()]
        if not match:
            console.print(f"[red]'{paid_by_name}' not in trip participants.[/]")
            sys.exit(1)
        paid_by_id = match[0]["id"]

    # Ask about recalculating shares if amount changes
    recalculate = False
    if amount is not None:
        recalculate = True

    try:
        updated = db.update_expense(
            expense_id=expense_id,
            description=description,
            expense_date=expense_date,
            category_id=category_id,
            amount=amount,
            paid_by=paid_by_id,
            recalculate_shares=recalculate,
        )
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        sys.exit(1)

    if updated:
        console.print(f"[green]✅ Updated expense #{expense_id}[/]")
        if recalculate:
            console.print(f"   ⚠️  Amount changed — shares recalculated.")
    else:
        console.print(f"[red]#{expense_id} not found.[/]")


@exp.command("delete")
@click.argument("expense_id", type=int)
def exp_delete(expense_id):
    """Delete an expense."""
    if db.delete_expense(expense_id):
        console.print(f"[green]🗑️ Deleted #{expense_id}[/]")
    else:
        console.print(f"[red]#{expense_id} not found.[/]")


# ─── Settlement & Summary ──────────────────────────────────────────────

def _print_settlement(s):
    trip_name = s["trip"]["name"]
    currency = s["trip"]["currency"]
    days = 1
    if s["trip"]["start_date"]:
        end = s["trip"]["end_date"] or date.today().isoformat()
        days = (date.fromisoformat(end) - date.fromisoformat(s["trip"]["start_date"])).days + 1

    console.print(Panel(f"[bold]{trip_name}[/]  —  {days} days  |  {s['count']} expenses  |  {fmt(s['total'], currency)}"))
    per_day = s["total"] / days if days else 0
    console.print(f"   Total: [bold]{fmt(s['total'], currency)}[/]  |  Daily avg: {fmt(per_day, currency)}")

    # By category
    if s["by_category"]:
        console.print("\n[bold]📊 By Category[/]")
        t = Table(box=box.SIMPLE)
        t.add_column("Category")
        t.add_column("Amount")
        t.add_column("Count")
        t.add_column("%")
        for c in s["by_category"]:
            pct = (c["total"] / s["total"] * 100) if s["total"] else 0
            t.add_row(f"{c['emoji']} {c['name']}", fmt(c["total"], currency), str(c["count"]), f"{pct:.0f}%")
        console.print(t)

    # By person
    if s["by_person"]:
        console.print("\n[bold]👤 Who Paid What[/]")
        t = Table(box=box.SIMPLE)
        t.add_column("Person")
        t.add_column("Total Paid")
        t.add_column("Expenses")
        for p in s["by_person"]:
            t.add_row(p["name"], fmt(p["total"], currency), str(p["count"]))
        console.print(t)

    # Balances
    console.print("\n[bold]💰 Net Balances[/]")
    bal_t = Table(box=box.SIMPLE)
    bal_t.add_column("Person")
    bal_t.add_column("Paid")
    bal_t.add_column("Owes")
    bal_t.add_column("Balance")
    for b in s["balances"]:
        bal = b["balance"]
        bal_str = f"[green]+{fmt(bal, currency)}[/]" if bal > 0 else (f"[red]{fmt(bal, currency)}[/]" if bal < 0 else "[dim]0[/]")
        bal_t.add_row(b["name"], fmt(b["paid"], currency), fmt(b["owed"], currency), bal_str)
    console.print(bal_t)

    # Settlements
    if s["settlements"]:
        console.print("\n[bold]🤝 Settle Up[/]")
        for st in s["settlements"]:
            console.print(f"   {st['from']} → [bold]{st['to']}[/]  {fmt(st['amount'], currency)}")
    else:
        console.print("\n[green]✅ All settled! Nobody owes anything.[/]")


@cli.command()
@click.argument("trip_id", type=int, required=False)
def summary(trip_id):
    """Show expense summary + settlements for a trip."""
    if trip_id is None:
        t = _pick_active_trip()
        trip_id = t["id"]
    s = db.compute_settlement(trip_id)
    if not s:
        console.print("[red]Trip not found.[/]")
        return
    _print_settlement(s)


@cli.command()
@click.argument("trip_id", type=int, required=False)
@click.option("--format", "-f", "type", type=click.Choice(["csv", "json", "table"]), default="table")
@click.option("--output", "-o", "outfile", default=None, help="Save to file")
def export(trip_id, type, outfile):
    """Export expense data."""
    if trip_id is None:
        t = _pick_active_trip()
        trip_id = t["id"]
    t = db.get_trip(trip_id)
    if not t:
        console.print("[red]Trip not found.[/]")
        return
    rows = db.get_expenses(trip_id=trip_id, limit=9999)
    currency = t["currency"]

    if type == "json":
        data = []
        for r in rows:
            shares = db.get_expense_shares(r["id"])
            data.append({
                "id": r["id"],
                "date": r["expense_date"],
                "category": r["category"],
                "amount": r["amount"],
                "currency": r["currency"],
                "paid_by": r["paid_by_name"],
                "split_type": r["split_type"],
                "description": r["description"],
                "shares": [{"name": s["name"], "amount": s["share_amount"]} for s in shares],
            })
        output = json.dumps(data, indent=2, ensure_ascii=False)
    elif type == "csv":
        lines = ["id,date,category,amount,currency,paid_by,split_type,description"]
        for r in rows:
            desc = r["description"].replace('"', '""') if r["description"] else ""
            lines.append(f'{r["id"]},{r["expense_date"]},{r["category"]},{r["amount"]},{r["currency"]},{r["paid_by_name"]},{r["split_type"]},"{desc}"')
        output = "\n".join(lines) + "\n"
    else:
        table = Table(title=f"All Expenses — {t['name']}")
        table.add_column("Date")
        table.add_column("Category")
        table.add_column("Amount")
        table.add_column("Paid By")
        table.add_column("Description")
        for r in rows:
            table.add_row(
                r["expense_date"], f"{r['emoji']} {r['category']}",
                fmt(r["amount"], currency), r["paid_by_name"],
                r["description"] or "—",
            )
        console.print(table)
        return

    if outfile:
        with open(outfile, "w") as f:
            f.write(output)
        console.print(f"[green]✅ Exported to {outfile}[/]")
    else:
        console.print(output)


# ─── Categories ────────────────────────────────────────────────────────

@cli.command()
def cats():
    """List expense categories."""
    cats = db.list_categories()
    t = Table(title="Categories")
    t.add_column("ID", style="dim")
    t.add_column("Category")
    for c in cats:
        t.add_row(str(c["id"]), f"{c['emoji']} {c['name']}")
    console.print(t)
