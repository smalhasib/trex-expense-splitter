"""SQLite database layer for tour expense splitter."""

import sqlite3
import os
from pathlib import Path
from datetime import date, datetime
from collections import defaultdict

DB_DIR = Path.home() / ".tourexpenses"
DB_PATH = DB_DIR / "expenses.db"


def get_conn() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trips (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            destination TEXT    NOT NULL DEFAULT '',
            start_date  TEXT    NOT NULL,
            end_date    TEXT,
            is_active   INTEGER NOT NULL DEFAULT 1,
            currency    TEXT    NOT NULL DEFAULT 'BDT',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS participants (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id   INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
            name      TEXT    NOT NULL,
            joined_on TEXT    NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1, -- New column
            UNIQUE(trip_id, name)
        );

        CREATE TABLE IF NOT EXISTS categories (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name  TEXT    NOT NULL UNIQUE,
            emoji TEXT    NOT NULL DEFAULT '📦'
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id     INTEGER NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            amount      REAL    NOT NULL CHECK(amount > 0),
            currency    TEXT    NOT NULL DEFAULT 'BDT',
            description TEXT    NOT NULL DEFAULT '',
            paid_by     INTEGER NOT NULL REFERENCES participants(id),
            split_type  TEXT    NOT NULL DEFAULT 'equal' CHECK(split_type IN ('equal', 'custom')),
            expense_date TEXT   NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS expense_shares (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id    INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
            participant_id INTEGER NOT NULL REFERENCES participants(id),
            share_amount  REAL    NOT NULL CHECK(share_amount >= 0),
            UNIQUE(expense_id, participant_id)
        );

        -- Default categories
        INSERT OR IGNORE INTO categories (id, name, emoji) VALUES
            (1, 'Food & Drink',    '🍽️'),
            (2, 'Transport',       '🚕'),
            (3, 'Accommodation',   '🏨'),
            (4, 'Activities',      '🎯'),
            (5, 'Shopping',        '🛍️'),
            (6, 'Tickets & Entry', '🎟️'),
            (7, 'Fuel',            '⛽'),
            (8, 'Miscellaneous',   '📦');
    """)

    # Migration: add joined_on if missing
    try:
        conn.execute("ALTER TABLE participants ADD COLUMN joined_on TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists

    # Migration: add is_active if missing
    try:
        conn.execute("ALTER TABLE participants ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.commit()
    conn.close()


# ─── Trips ──────────────────────────────────────────────────────────────

def create_trip(name: str, destination: str = "", currency: str = "BDT") -> int:
    conn = get_conn()
    today = date.today().isoformat()
    cur = conn.execute(
        "INSERT INTO trips (name, destination, start_date, currency) VALUES (?, ?, ?, ?)",
        (name, destination, today, currency.upper()),
    )
    trip_id = cur.lastrowid
    conn.commit()
    conn.close()
    return trip_id


def close_trip(trip_id: int):
    conn = get_conn()
    today = date.today().isoformat()
    conn.execute(
        "UPDATE trips SET end_date = ?, is_active = 0 WHERE id = ?",
        (today, trip_id),
    )
    conn.commit()
    conn.close()


def reopen_trip(trip_id: int):
    conn = get_conn()
    conn.execute(
        "UPDATE trips SET end_date = NULL, is_active = 1 WHERE id = ?",
        (trip_id,),
    )
    conn.commit()
    conn.close()


def list_trips(include_closed: bool = False) -> list[sqlite3.Row]:
    conn = get_conn()
    if include_closed:
        rows = conn.execute(
            "SELECT id, name, destination, start_date, end_date, is_active, currency FROM trips ORDER BY id DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, destination, start_date, end_date, is_active, currency FROM trips WHERE is_active=1 ORDER BY id DESC"
        ).fetchall()
    conn.close()
    return rows


def get_trip(trip_id: int) -> sqlite3.Row | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
    conn.close()
    return row


# ─── Participants ───────────────────────────────────────────────────────

def add_participant(trip_id: int, name: str, joined_on: str | None = None) -> int:
    conn = get_conn()
    if not joined_on:
        # Default to today's date if not provided
        joined_on = date.today().isoformat()
    try:
        cur = conn.execute(
            "INSERT INTO participants (trip_id, name, joined_on) VALUES (?, ?, ?)",
            (trip_id, name, joined_on),
        )
        pid = cur.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        pid = conn.execute(
            "SELECT id FROM participants WHERE trip_id = ? AND name = ?",
            (trip_id, name),
        ).fetchone()[0]
    finally:
        conn.close()
    return pid


def remove_participant(trip_id: int, name: str) -> bool:
    conn = get_conn()
    # First, check if participant has any expenses
    has_expenses = conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE paid_by = (SELECT id FROM participants WHERE trip_id = ? AND name = ?)",
        (trip_id, name),
    ).fetchone()[0] > 0

    if has_expenses:
        # Soft delete
        cur = conn.execute(
            "UPDATE participants SET is_active = 0 WHERE trip_id = ? AND name = ?",
            (trip_id, name),
        )
    else:
        # Hard delete if no expenses
        cur = conn.execute(
            "DELETE FROM participants WHERE trip_id = ? AND name = ?",
            (trip_id, name),
        )
    removed = cur.rowcount > 0
    conn.commit()
    conn.close()
    return removed


def get_participants(trip_id: int) -> list[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, joined_on, is_active FROM participants WHERE trip_id = ? AND is_active = 1 ORDER BY id",
        (trip_id,),
    ).fetchall()
    conn.close()
    return rows


def get_all_participants(trip_id: int) -> list[sqlite3.Row]:
    """Return ALL participants including soft-deleted (for settlement math)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, joined_on, is_active FROM participants WHERE trip_id = ? ORDER BY id",
        (trip_id,),
    ).fetchall()
    conn.close()
    return rows


def list_categories() -> list[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute("SELECT id, name, emoji FROM categories ORDER BY id").fetchall()
    conn.close()
    return rows


# ─── Expenses ───────────────────────────────────────────────────────────

def add_expense(
    trip_id: int,
    category_id: int,
    amount: float,
    paid_by: int,
    description: str = "",
    expense_date: str | None = None,
    split_type: str = "equal",
    custom_shares: dict[int, float] | None = None,
    split_for: list[str] | None = None,
) -> int:
    """Add an expense.
    
    Args:
        trip_id: Trip ID
        category_id: Category ID
        amount: Total amount
        paid_by: Participant ID who paid
        description: Optional description
        expense_date: Date string, defaults to today
        split_type: 'equal' or 'custom'
        custom_shares: {participant_id: share_amount} for custom split
        split_for: Names of people to split among (equal only).
                   If None, splits among everyone joined as of expense_date.
    """
    conn = get_conn()
    edate = expense_date or date.today().isoformat()
    
    cur = conn.execute(
        "INSERT INTO expenses (trip_id, category_id, amount, description, paid_by, split_type, expense_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (trip_id, category_id, amount, description, paid_by, split_type, edate),
    )
    expense_id = cur.lastrowid

    # Create shares
    if split_type == "equal":
        all_people = get_participants(trip_id)
        if split_for:
            # Split only among named participants
            names_lower = [n.strip().lower() for n in split_for]
            valid_names = {p["name"].lower() for p in all_people}
            invalid = [n for n in names_lower if n not in valid_names]
            if invalid:
                raise ValueError(
                    f"--for contains unknown names: {invalid}. "
                    f"Available: {[p['name'] for p in all_people]}"
                )
            people = [p for p in all_people if p["name"].lower() in names_lower]
        else:
            # Auto-filter by join date: only those who joined on or before the expense date
            people = [p for p in all_people if not p["joined_on"] or p["joined_on"] <= edate]
        
        if not people:
            people = all_people  # fallback if all filtered out

        per_person = round(amount / len(people), 2)
        total_shares = per_person * len(people)
        diff = round(amount - total_shares, 2)
        
        for i, p in enumerate(people):
            share = per_person + (diff if i == len(people) - 1 else 0)
            conn.execute(
                "INSERT INTO expense_shares (expense_id, participant_id, share_amount) VALUES (?, ?, ?)",
                (expense_id, p["id"], round(share, 2)),
            )
    elif split_type == "custom" and custom_shares:
        total_custom = round(sum(custom_shares.values()), 2)
        if abs(total_custom - amount) > 0.01:
            raise ValueError(
                f"Custom shares sum to {total_custom} but expense is {amount}"
            )
        for pid, share in custom_shares.items():
            if share > 0:
                conn.execute(
                    "INSERT INTO expense_shares (expense_id, participant_id, share_amount) VALUES (?, ?, ?)",
                    (expense_id, pid, round(share, 2)),
                )

    conn.commit()
    conn.close()
    return expense_id


def update_expense(
    expense_id: int,
    description: str | None = None,
    expense_date: str | None = None,
    category_id: int | None = None,
    amount: float | None = None,
    paid_by: int | None = None,
    recalculate_shares: bool = False,
) -> bool:
    """Update an expense.
    
    Simple field updates (description, date, category, paid_by) are direct.
    If `amount` or `paid_by` changes, the caller should set recalculate_shares=True
    to have the equal-split shares recalculated automatically.
    """
    conn = get_conn()
    
    fields = []
    params = []
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if expense_date is not None:
        fields.append("expense_date = ?")
        params.append(expense_date)
    if category_id is not None:
        fields.append("category_id = ?")
        params.append(category_id)
    if amount is not None:
        if amount <= 0:
            conn.close()
            raise ValueError("Amount must be positive")
        fields.append("amount = ?")
        params.append(amount)
    if paid_by is not None:
        fields.append("paid_by = ?")
        params.append(paid_by)
    
    if not fields and not recalculate_shares:
        conn.close()
        return False  # Nothing to update
    
    if fields:
        params.append(expense_id)
        conn.execute(
            f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?",
            params,
        )

    if recalculate_shares and amount is not None:
        # Recalculate equal-split shares among all participants (active only)
        conn.execute("DELETE FROM expense_shares WHERE expense_id = ?", (expense_id,))
        trip_row = conn.execute("SELECT trip_id, split_type FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if trip_row and trip_row["split_type"] == "equal":
            people = get_participants(trip_row["trip_id"])
            if people:
                per_person = round(amount / len(people), 2)
                total_shares = per_person * len(people)
                diff = round(amount - total_shares, 2)
                for i, p in enumerate(people):
                    share = per_person + (diff if i == len(people) - 1 else 0)
                    conn.execute(
                        "INSERT INTO expense_shares (expense_id, participant_id, share_amount) VALUES (?, ?, ?)",
                        (expense_id, p["id"], round(share, 2)),
                    )

    conn.commit()
    conn.close()
    return True


def get_expenses(
    trip_id: int | None = None,
    category_id: int | None = None,
    limit: int = 100,
) -> list[sqlite3.Row]:
    conn = get_conn()
    parts = [
        "SELECT e.id, e.amount, e.currency, e.description, e.expense_date, e.split_type, e.created_at,"
        " c.name AS category, c.emoji, t.name AS trip_name,"
        " pp.name AS paid_by_name, pp.id AS paid_by_id"
        " FROM expenses e"
        " JOIN categories c ON c.id = e.category_id"
        " JOIN trips t ON t.id = e.trip_id"
        " JOIN participants pp ON pp.id = e.paid_by"
    ]
    wheres = []
    params = []
    if trip_id is not None:
        wheres.append("e.trip_id = ?")
        params.append(trip_id)
    if category_id is not None:
        wheres.append("e.category_id = ?")
        params.append(category_id)
    if wheres:
        parts.append(" WHERE " + " AND ".join(wheres))
    parts.append(" ORDER BY e.expense_date DESC, e.id DESC LIMIT ?")
    params.append(limit)
    rows = conn.execute(" ".join(parts), params).fetchall()
    conn.close()
    return rows


# ─── Settlements ────────────────────────────────────────────────────────

def compute_settlement(trip_id: int) -> dict:
    """Compute who owes whom.
    
    Returns:
        {
            'trip': trip dict,
            'total': total amount,
            'count': expense count,
            'participants': [{'id', 'name', 'paid', 'owed', 'balance'}, ...],
            'settlements': [{'from': name, 'to': name, 'amount': float}, ...],
            'by_category': [...],
            'by_person': [...]
        }
    """
    conn = get_conn()
    trip = conn.execute("SELECT * FROM trips WHERE id = ?", (trip_id,)).fetchone()
    if not trip:
        conn.close()
        return {}

    people = get_all_participants(trip_id)
    if not people:
        conn.close()
        return {}

    # Total paid by each person (sum of their expenses)
    paid_by_person = {}
    for p in people:
        paid = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE trip_id = ? AND paid_by = ?",
            (trip_id, p["id"]),
        ).fetchone()[0]
        paid_by_person[p["id"]] = {"name": p["name"], "paid": paid}

    # What each person owes (sum of their shares in all expenses)
    owed_by_person = defaultdict(float)
    for p in people:
        owed = conn.execute(
            "SELECT COALESCE(SUM(es.share_amount), 0)"
            " FROM expense_shares es"
            " JOIN expenses e ON e.id = es.expense_id"
            " WHERE e.trip_id = ? AND es.participant_id = ?",
            (trip_id, p["id"]),
        ).fetchone()[0]
        owed_by_person[p["id"]] = owed

    # Net balance: positive = they're owed money, negative = they owe
    balances = {}
    for p in people:
        pid = p["id"]
        paid_val = paid_by_person[pid]["paid"]
        owed_val = owed_by_person[pid]
        net = round(paid_val - owed_val, 2)
        balances[pid] = {
            "id": pid,
            "name": p["name"],
            "paid": round(paid_val, 2),
            "owed": round(owed_val, 2),
            "balance": net,
        }

    # Greedy settlement: who gets paid by whom
    # Use copies so we don't mutate the original balances
    creditors = sorted([dict(b) for b in balances.values() if b["balance"] > 0],
                       key=lambda x: -x["balance"])
    debtors = sorted([dict(b) for b in balances.values() if b["balance"] < 0],
                     key=lambda x: x["balance"])

    settlements = []
    i, j = 0, 0
    while i < len(creditors) and j < len(debtors):
        amount = min(creditors[i]["balance"], -debtors[j]["balance"])
        if amount > 0.01:  # Ignore tiny rounding errors
            settlements.append({
                "from": debtors[j]["name"],
                "to": creditors[i]["name"],
                "amount": round(amount, 2),
            })
            creditors[i]["balance"] = round(creditors[i]["balance"] - amount, 2)
            debtors[j]["balance"] = round(debtors[j]["balance"] + amount, 2)
        if creditors[i]["balance"] < 0.01:
            i += 1
        if debtors[j]["balance"] > -0.01:
            j += 1

    # Category breakdown
    by_cat = conn.execute(
        "SELECT c.name, c.emoji, COALESCE(SUM(e.amount), 0) AS total, COUNT(*) AS count"
        " FROM expenses e"
        " JOIN categories c ON c.id = e.category_id"
        " WHERE e.trip_id = ?"
        " GROUP BY c.id, c.name, c.emoji"
        " ORDER BY total DESC",
        (trip_id,),
    ).fetchall()

    # Per-person breakdown
    by_person = conn.execute(
        "SELECT pp.name, COALESCE(SUM(e.amount), 0) AS total, COUNT(*) AS count"
        " FROM expenses e"
        " JOIN participants pp ON pp.id = e.paid_by"
        " WHERE e.trip_id = ?"
        " GROUP BY pp.id, pp.name"
        " ORDER BY total DESC",
        (trip_id,),
    ).fetchall()

    total = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE trip_id = ?",
        (trip_id,),
    ).fetchone()[0]

    count = conn.execute(
        "SELECT COUNT(*) FROM expenses WHERE trip_id = ?", (trip_id,)
    ).fetchone()[0]

    conn.close()

    return {
        "trip": dict(trip),
        "total": total,
        "count": count,
        "balances": list(balances.values()),
        "settlements": settlements,
        "by_category": [dict(r) for r in by_cat],
        "by_person": [dict(r) for r in by_person],
    }


# ─── Utilities ──────────────────────────────────────────────────────────

def search_expenses(trip_id: int | None, keyword: str, limit: int = 20) -> list[sqlite3.Row]:
    conn = get_conn()
    parts = [
        "SELECT e.id, e.amount, e.currency, e.description, e.expense_date,"
        " c.name AS category, c.emoji, t.name AS trip_name,"
        " pp.name AS paid_by_name"
        " FROM expenses e"
        " JOIN categories c ON c.id = e.category_id"
        " JOIN trips t ON t.id = e.trip_id"
        " JOIN participants pp ON pp.id = e.paid_by"
        " WHERE e.description LIKE ?"
    ]
    params = [f"%{keyword}%"]
    if trip_id:
        parts.append(" AND e.trip_id = ?")
        params.append(trip_id)
    parts.append(" ORDER BY e.expense_date DESC LIMIT ?")
    params.append(limit)
    rows = conn.execute(" ".join(parts), params).fetchall()
    conn.close()
    return rows


def delete_expense(expense_id: int) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_expense_shares(expense_id: int) -> list[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT es.participant_id, p.name, es.share_amount"
        " FROM expense_shares es"
        " JOIN participants p ON p.id = es.participant_id"
        " WHERE es.expense_id = ?",
        (expense_id,),
    ).fetchall()
    conn.close()
    return rows


def get_expense_trip_id(expense_id: int) -> int | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT trip_id FROM expenses WHERE id = ?", (expense_id,)
    ).fetchone()
    conn.close()
    return row["trip_id"] if row else None
