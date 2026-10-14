"""Campus Customs MCP server (FastMCP).

Every agent on the Campus Customs team gets its shop facts from the tools in
this file, and only from these tools. The tools talk to the working copy of
the shop database, data/campus_customs_new.db; the original
data/campus_customs.db is never opened here.

Rules every tool follows:
  - Only report what is in the database. If a row is missing, say so
    ("found": false) instead of guessing.
  - "Today" is desk.date_today, never the computer clock.
  - Money math is done here in code, so agents do not do arithmetic in prose.
    Amounts for payments are read from the invoice, lease or pricing row;
    an agent can never type in its own amount.
  - No tool an agent can call moves money. Agents only *prepare* payment
    requests. Cash changes only in approve_payment_request, which is for a
    human (the dashboard's approve button); the backend blocks every agent
    from calling it.
  - Nothing is ever sent outside the shop. Customer messages are saved as
    drafts for the board.

Tables this server adds to the working copy (created on first use, so a reset
to the original file simply starts them empty):
  payment_requests  pay / purchase-order requests waiting for a human
  quotes            draft price quotes (e.g. a bulk discount)
  message_drafts    customer messages that are never sent
  ticket_updates    history of ticket status changes

Run it (stdio):  ../.venv/bin/python server.py
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

from fastmcp import FastMCP

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("CAMPUS_DB", ROOT / "data" / "campus_customs_new.db"))

mcp = FastMCP("campus-customs")

TICKET_STATUSES = ("open", "in_progress", "waiting_on_human", "resolved")

EXTRA_TABLES = """
CREATE TABLE IF NOT EXISTS payment_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER,
    kind TEXT NOT NULL,              -- invoice | rent | purchase_order
    ref_id INTEGER,                  -- invoice id, lease id, or NULL for a PO
    payee TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT NOT NULL,
    vendor_id INTEGER,
    sku TEXT, size TEXT, qty INTEGER,
    expected_arrival TEXT,
    status TEXT NOT NULL,            -- pending | approved | rejected
    requested_by TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    decided_by TEXT,
    decided_at TEXT,
    decision_note TEXT,
    payment_id INTEGER
);
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    sku TEXT NOT NULL, size TEXT NOT NULL, qty INTEGER NOT NULL,
    list_price REAL NOT NULL, unit_cost REAL NOT NULL,
    quoted_unit_price REAL NOT NULL,
    discount_pct REAL NOT NULL,
    margin_per_unit REAL NOT NULL,
    total_price REAL NOT NULL,
    total_margin REAL NOT NULL,
    status TEXT NOT NULL,            -- draft (a human confirms with the customer)
    prepared_by TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS message_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL,            -- draft (never sent)
    written_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    old_status TEXT, new_status TEXT NOT NULL,
    note TEXT,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _connect(write: bool = False) -> sqlite3.Connection:
    """Connection to the working database (read-only unless write=True)."""
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Working database not found: {DB_PATH}")
    mode = "rw" if write else "ro"
    conn = sqlite3.connect(f"file:{DB_PATH}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    if write:
        conn.executescript(EXTRA_TABLES)
    return conn


def _has_table(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone() is not None


def _today(conn: sqlite3.Connection) -> str:
    """The shop's 'today' from desk.date_today."""
    return conn.execute("SELECT date_today FROM desk LIMIT 1").fetchone()["date_today"]


def _days_between(start: str, end: str) -> int:
    """Whole days from start to end (both YYYY-MM-DD)."""
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _stamp() -> str:
    """Wall-clock time for audit columns (when the agent acted)."""
    return datetime.now().isoformat(timespec="seconds")


def _checking(conn: sqlite3.Connection) -> float:
    return conn.execute("SELECT balance FROM cash_accounts WHERE name = 'checking'").fetchone()["balance"]


def _pending_total(conn: sqlite3.Connection) -> float:
    if not _has_table(conn, "payment_requests"):
        return 0.0
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payment_requests WHERE status = 'pending'"
    ).fetchone()[0]


def _open_invoices(conn: sqlite3.Connection, vendor_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT id, amount, due_date FROM invoices WHERE vendor_id = ? AND status = 'open'",
        (vendor_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _add_month(iso_day: str) -> str:
    """Same day next month (clamped to the month's last day)."""
    d = date.fromisoformat(iso_day)
    year, month = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    for day in (d.day, 30, 29, 28):
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            continue
    raise ValueError(iso_day)


def _request_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


# --------------------------------------------------------------------------
# read tools
# --------------------------------------------------------------------------

@mcp.tool
def list_tickets(status: str | None = None) -> dict:
    """List the tickets on the desk board with their type, requester, subject
    and status, plus the shop's today. Leave status empty for all tickets, or
    pass one of: open, in_progress, waiting_on_human, resolved.
    """
    with _connect() as conn:
        sql = "SELECT id, type, requester, subject, status, created_at FROM tickets"
        args: tuple = ()
        if status:
            sql += " WHERE status = ?"
            args = (status,)
        rows = conn.execute(sql + " ORDER BY id", args).fetchall()
        return {"today": _today(conn), "count": len(rows), "tickets": [dict(r) for r in rows]}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Read one ticket in full: every field (sku, size, qty, lease_id,
    invoice_id, notes), plus everything the team has already prepared for it
    (payment requests, quotes, message drafts, status history).
    """
    with _connect() as conn:
        t = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"found": False, "ticket_id": ticket_id, "message": f"No ticket with id {ticket_id}."}
        out = {"found": True, "today": _today(conn), "ticket": dict(t)}
        for table, key in (("payment_requests", "payment_requests"), ("quotes", "quotes"),
                           ("message_drafts", "message_drafts"), ("ticket_updates", "status_history")):
            out[key] = (
                [dict(r) for r in conn.execute(f"SELECT * FROM {table} WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
                if _has_table(conn, table) else []
            )
        return out


@mcp.tool
def check_stock(sku: str, size: str, qty_needed: int = 1) -> dict:
    """Check how many units of a SKU in a given size are on the shelf, and
    whether that covers a request.

    Use for customer orders and bulk requests (for example ticket 101's white
    tee in S, or ticket 103's 20 navy hoodies in M). Also returns every other
    size of the same SKU and its unit cost and list price, so the team can
    see alternatives and margin without guessing.

    Args:
        sku: Product SKU, e.g. "CC-TEE-WHITE".
        size: Size code exactly as stored, e.g. "S", "M", "L", "XL", "OS".
        qty_needed: How many units the request asks for (default 1).
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ?",
            (sku,),
        ).fetchall()
        if not rows:
            return {"found": False, "sku": sku, "message": f"No inventory rows for SKU {sku}."}

        price = conn.execute(
            "SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)
        ).fetchone()

        match = next((r for r in rows if r["size"] == size), None)
        on_hand = match["qty"] if match else 0
        shortfall = max(qty_needed - on_hand, 0)

        return {
            "found": True,
            "sku": sku,
            "name": rows[0]["name"],
            "location": rows[0]["location"],
            "size": size,
            "size_exists": match is not None,
            "qty_on_hand": on_hand,
            "qty_needed": qty_needed,
            "shortfall": shortfall,
            "can_fill_from_stock": shortfall == 0,
            "all_sizes": {r["size"]: r["qty"] for r in rows},
            "unit_cost": price["unit_cost"] if price else None,
            "list_price": price["list_price"] if price else None,
            "margin_per_unit": round(price["list_price"] - price["unit_cost"], 2) if price else None,
        }


@mcp.tool
def find_vendors(specialty_keyword: str | None = None) -> dict:
    """List vendors who could restock, with specialty and lead time (from the
    vendors table only), and whether each will ship right now. A vendor with
    any open unpaid invoice will not ship new product.

    Args:
        specialty_keyword: optional word to match in the specialty, e.g.
            "apparel" or "mugs". Leave empty to list every vendor.
    """
    with _connect() as conn:
        today = _today(conn)
        sql, args = "SELECT * FROM vendors", ()
        if specialty_keyword:
            sql, args = sql + " WHERE specialty LIKE ?", (f"%{specialty_keyword}%",)
        vendors = []
        for v in conn.execute(sql + " ORDER BY id", args):
            open_inv = _open_invoices(conn, v["id"])
            vendors.append({
                **dict(v),
                "earliest_arrival_if_ordered_today": (date.fromisoformat(today) + timedelta(days=v["lead_days"])).isoformat(),
                "open_invoices": open_inv,
                "will_ship": not open_inv,
            })
        return {"today": today, "count": len(vendors), "vendors": vendors}


@mcp.tool
def get_invoice_status(invoice_id: int) -> dict:
    """Look up one vendor invoice: amount, due date, open or paid, how many
    days overdue it is as of the shop's today, and the vendor behind it
    (specialty and lead time).

    Shop rule: a vendor will not ship new product while it has an open unpaid
    invoice. The result says whether that rule is blocking this vendor right
    now. Ticket 101 links invoice 501 this way.

    Args:
        invoice_id: The invoice id, e.g. 501.
    """
    with _connect() as conn:
        inv = conn.execute(
            """SELECT i.id, i.vendor_id, i.amount, i.due_date, i.status, i.description,
                      v.name AS vendor_name, v.specialty, v.lead_days
               FROM invoices i JOIN vendors v ON v.id = i.vendor_id
               WHERE i.id = ?""",
            (invoice_id,),
        ).fetchone()
        if inv is None:
            return {"found": False, "invoice_id": invoice_id, "message": f"No invoice with id {invoice_id}."}

        today = _today(conn)
        open_for_vendor = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM invoices WHERE vendor_id = ? AND status = 'open'",
            (inv["vendor_id"],),
        ).fetchone()

        days_late = _days_between(inv["due_date"], today)
        is_open = inv["status"] == "open"
        return {
            "found": True,
            "today": today,
            "invoice_id": inv["id"],
            "description": inv["description"],
            "amount": inv["amount"],
            "due_date": inv["due_date"],
            "status": inv["status"],
            "is_overdue": is_open and days_late > 0,
            "days_overdue": days_late if is_open and days_late > 0 else 0,
            "vendor": {
                "id": inv["vendor_id"],
                "name": inv["vendor_name"],
                "specialty": inv["specialty"],
                "lead_days": inv["lead_days"],
            },
            "vendor_open_invoices": open_for_vendor[0],
            "vendor_open_amount": open_for_vendor[1],
            "vendor_will_ship": open_for_vendor[0] == 0,
        }


@mcp.tool
def get_lease_status(lease_id: int) -> dict:
    """Look up one shop lease: space, landlord, monthly rent, next due date,
    and how many days until (or past) that date as of the shop's today.

    Use for rent notices such as ticket 102, so the team checks the real
    amount and due date in the lease instead of trusting the landlord's email.

    Args:
        lease_id: The lease id, e.g. 1.
    """
    with _connect() as conn:
        lease = conn.execute(
            "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
            (lease_id,),
        ).fetchone()
        if lease is None:
            return {"found": False, "lease_id": lease_id, "message": f"No lease with id {lease_id}."}

        today = _today(conn)
        days_until = _days_between(today, lease["next_due"])
        return {
            "found": True,
            "today": today,
            "lease_id": lease["id"],
            "space_name": lease["space_name"],
            "landlord": lease["landlord"],
            "monthly_rent": lease["monthly_rent"],
            "next_due": lease["next_due"],
            "days_until_due": days_until,
            "is_overdue": days_until < 0,
            "notes": lease["notes"],
        }


@mcp.tool
def get_cash_balance() -> dict:
    """The checking balance from cash_accounts, the total of payment requests
    still waiting for a human, and what would be left if every one of them
    were approved. No money ever comes in (revenue is not modelled).
    """
    with _connect() as conn:
        row = conn.execute("SELECT name, balance, date FROM cash_accounts WHERE name = 'checking'").fetchone()
        pending = _pending_total(conn)
        paid = conn.execute("SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM payments").fetchone()
        return {
            "today": _today(conn),
            "account": row["name"],
            "balance": row["balance"],
            "balance_date": row["date"],
            "pending_requests_total": pending,
            "balance_if_all_pending_approved": round(row["balance"] - pending, 2),
            "payments_made_count": paid[1],
            "payments_made_total": paid[0],
        }


@mcp.tool
def list_payment_requests(status: str | None = "pending", ticket_id: int | None = None) -> dict:
    """List payment and purchase-order requests prepared by the team.

    Args:
        status: pending (default), approved, rejected, or empty for all.
        ticket_id: optional, only requests for this ticket.
    """
    with _connect() as conn:
        if not _has_table(conn, "payment_requests"):
            return {"count": 0, "requests": []}
        sql, args = "SELECT * FROM payment_requests WHERE 1 = 1", []
        if status:
            sql += " AND status = ?"
            args.append(status)
        if ticket_id is not None:
            sql += " AND ticket_id = ?"
            args.append(ticket_id)
        rows = [dict(r) for r in conn.execute(sql + " ORDER BY id", args)]
        return {"count": len(rows), "total": round(sum(r["amount"] for r in rows), 2), "requests": rows}


# --------------------------------------------------------------------------
# write tools agents may use (none of these moves money or contacts anyone)
# --------------------------------------------------------------------------

@mcp.tool
def prepare_payment(kind: Literal["invoice", "rent"], ref_id: int, ticket_id: int,
                    requested_by: str, reason: str) -> dict:
    """Prepare (do NOT make) a payment of an open invoice or of rent, for a
    human to approve on the dashboard. The amount and payee are read from the
    invoices or leases table; the caller cannot set them. Cash does not
    change here.

    Args:
        kind: "invoice" (ref_id = invoices.id) or "rent" (ref_id = leases.id).
        ref_id: the invoice id or lease id.
        ticket_id: the ticket this payment resolves.
        requested_by: the agent preparing it, e.g. "accounting".
        reason: one or two sentences a human approver can read.
    """
    with _connect(write=True) as conn:
        today = _today(conn)
        if kind == "invoice":
            row = conn.execute(
                "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                (ref_id,),
            ).fetchone()
            if row is None:
                return {"ok": False, "message": f"No invoice with id {ref_id}."}
            if row["status"] != "open":
                return {"ok": False, "message": f"Invoice {ref_id} is '{row['status']}', not open; nothing to pay."}
            amount, payee, vendor_id = row["amount"], row["vendor_name"], row["vendor_id"]
        else:
            row = conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if row is None:
                return {"ok": False, "message": f"No lease with id {ref_id}."}
            amount, payee, vendor_id = row["monthly_rent"], row["landlord"], None

        dup = conn.execute(
            "SELECT id FROM payment_requests WHERE kind = ? AND ref_id = ? AND status = 'pending'",
            (kind, ref_id),
        ).fetchone()
        if dup:
            return {"ok": False, "message": f"A pending request (#{dup['id']}) already exists for this {kind}.",
                    "request_id": dup["id"]}

        balance, pending = _checking(conn), _pending_total(conn)
        cur = conn.execute(
            """INSERT INTO payment_requests (ticket_id, kind, ref_id, payee, amount, reason, vendor_id,
                   status, requested_by, requested_at) VALUES (?,?,?,?,?,?,?, 'pending', ?, ?)""",
            (ticket_id, kind, ref_id, payee, amount, reason, vendor_id, requested_by, _stamp()),
        )
        return {
            "ok": True,
            "request_id": cur.lastrowid,
            "status": "pending",
            "kind": kind, "ref_id": ref_id, "payee": payee, "amount": amount,
            "today": today,
            "checking_balance_now": balance,
            "balance_if_all_pending_approved": round(balance - pending - amount, 2),
            "affordable_with_other_pending": balance - pending - amount >= 0,
            "message": "Prepared only. A human must approve it on the dashboard before any cash moves.",
        }


@mcp.tool
def prepare_purchase_order(sku: str, size: str, qty: int, vendor_id: int, ticket_id: int,
                           requested_by: str, reason: str) -> dict:
    """Prepare (do NOT place) a restock purchase order for a human to
    approve. Cost = qty x pricing.unit_cost, read from the database. The
    expected arrival is today + vendors.lead_days. If the vendor has an open
    invoice, the request is still saved but marked as blocked: a human will
    not be able to approve it until that invoice is paid.

    Args:
        sku, size, qty: what to restock.
        vendor_id: vendors.id of the vendor to buy from.
        ticket_id: the ticket the restock is for.
        requested_by: the agent preparing it.
        reason: one or two sentences for the approver.
    """
    if qty <= 0:
        return {"ok": False, "message": "qty must be a positive whole number."}
    with _connect(write=True) as conn:
        today = _today(conn)
        price = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if price is None:
            return {"ok": False, "message": f"No pricing row for SKU {sku}; cannot cost a purchase order."}
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            return {"ok": False, "message": f"{sku} has no size {size} in inventory."}
        vendor = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
        if vendor is None:
            return {"ok": False, "message": f"No vendor with id {vendor_id}."}

        amount = round(qty * price["unit_cost"], 2)
        arrival = (date.fromisoformat(today) + timedelta(days=vendor["lead_days"])).isoformat()
        blockers = _open_invoices(conn, vendor_id)
        balance, pending = _checking(conn), _pending_total(conn)
        if amount > balance:
            # No money ever comes in, so this order could never be approved.
            return {"ok": False, "amount": amount, "checking_balance_now": balance,
                    "message": f"Refused: {qty} x {sku} costs ${amount:.2f} but checking holds only ${balance:.2f}, "
                               "and no money comes in. Offer what is on the shelf instead."}
        cur = conn.execute(
            """INSERT INTO payment_requests (ticket_id, kind, ref_id, payee, amount, reason, vendor_id,
                   sku, size, qty, expected_arrival, status, requested_by, requested_at)
               VALUES (?, 'purchase_order', NULL, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (ticket_id, vendor["name"], amount, reason, vendor_id, sku, size, qty, arrival, requested_by, _stamp()),
        )
        return {
            "ok": True,
            "request_id": cur.lastrowid,
            "status": "pending",
            "vendor": vendor["name"], "lead_days": vendor["lead_days"],
            "sku": sku, "size": size, "qty": qty,
            "unit_cost": price["unit_cost"], "amount": amount,
            "expected_arrival_if_approved_today": arrival,
            "blocked_by_open_invoices": blockers,
            "vendor_will_ship_now": not blockers,
            "checking_balance_now": balance,
            "balance_if_all_pending_approved": round(balance - pending - amount, 2),
            "affordable_with_other_pending": balance - pending - amount >= 0,
            "message": ("Prepared only; a human must approve it." if not blockers else
                        "Prepared, but the vendor has an open invoice: approval will be refused until it is paid."),
        }


@mcp.tool
def prepare_price_quote(ticket_id: int, sku: str, size: str, qty: int, discount_pct: float,
                        prepared_by: str, note: str = "") -> dict:
    """Prepare a draft price quote (for example a bulk discount). The tool
    reads list price and unit cost from pricing and works out unit price,
    margin and totals. It refuses any quote at or below cost. The quote is a
    draft: a human confirms it with the customer.

    Args:
        ticket_id: the ticket asking for the price.
        sku, size, qty: what is being quoted.
        discount_pct: percent off list price, 0-100 (e.g. 10 for 10% off).
        prepared_by: the agent preparing it.
        note: optional short explanation.
    """
    if qty <= 0 or not 0 <= discount_pct < 100:
        return {"ok": False, "message": "qty must be positive and discount_pct between 0 and 100."}
    with _connect(write=True) as conn:
        p = conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if p is None:
            return {"ok": False, "message": f"No pricing row for SKU {sku}."}
        unit_price = round(p["list_price"] * (1 - discount_pct / 100), 2)
        margin = round(unit_price - p["unit_cost"], 2)
        if margin <= 0:
            return {"ok": False, "message": f"{discount_pct}% off gives ${unit_price}, at or below the ${p['unit_cost']} cost. Refused.",
                    "max_discount_pct_above_cost": round((1 - p["unit_cost"] / p["list_price"]) * 100, 1)}
        on_hand = conn.execute("SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        cur = conn.execute(
            """INSERT INTO quotes (ticket_id, sku, size, qty, list_price, unit_cost, quoted_unit_price, discount_pct,
                   margin_per_unit, total_price, total_margin, status, prepared_by, note, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?, 'draft', ?, ?, ?)""",
            (ticket_id, sku, size, qty, p["list_price"], p["unit_cost"], unit_price, discount_pct, margin,
             round(unit_price * qty, 2), round(margin * qty, 2), prepared_by, note, _stamp()),
        )
        return {
            "ok": True, "quote_id": cur.lastrowid, "status": "draft",
            "sku": sku, "size": size, "qty": qty,
            "list_price": p["list_price"], "unit_cost": p["unit_cost"],
            "discount_pct": discount_pct, "quoted_unit_price": unit_price,
            "margin_per_unit": margin, "margin_pct_of_price": round(margin / unit_price * 100, 1),
            "total_price": round(unit_price * qty, 2), "total_margin": round(margin * qty, 2),
            "qty_on_hand_in_size": on_hand["qty"] if on_hand else 0,
        }


@mcp.tool
def draft_customer_message(ticket_id: int, recipient: str, subject: str, body: str, written_by: str) -> dict:
    """Save a message to a customer or partner as a DRAFT on the board. It is
    never emailed or sent anywhere; a human reads it and decides.

    Args:
        ticket_id: the ticket the message answers.
        recipient: who it is for, as written on the ticket (e.g. the requester).
        subject: short subject line.
        body: the full message text.
        written_by: the agent writing it, e.g. "customer_service".
    """
    with _connect(write=True) as conn:
        if conn.execute("SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)).fetchone() is None:
            return {"ok": False, "message": f"No ticket with id {ticket_id}."}
        cur = conn.execute(
            """INSERT INTO message_drafts (ticket_id, recipient, subject, body, status, written_by, created_at)
               VALUES (?,?,?,?, 'draft', ?, ?)""",
            (ticket_id, recipient, subject, body, written_by, _stamp()),
        )
        return {"ok": True, "draft_id": cur.lastrowid, "status": "draft",
                "message": "Saved as a draft on the board. Nothing was sent."}


@mcp.tool
def update_ticket_status(ticket_id: int, status: Literal["open", "in_progress", "waiting_on_human", "resolved"],
                         note: str, updated_by: str) -> dict:
    """Change a ticket's status and record why in the ticket history.

    Use "waiting_on_human" when the team has done its part but a payment or
    purchase still needs a human's approval, and "resolved" when nothing is
    left for the team to do. A ticket cannot be marked resolved while one of
    its payment requests is still pending.
    """
    with _connect(write=True) as conn:
        t = conn.execute("SELECT status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if t is None:
            return {"ok": False, "message": f"No ticket with id {ticket_id}."}
        pending = conn.execute(
            "SELECT COUNT(*) FROM payment_requests WHERE ticket_id = ? AND status = 'pending'", (ticket_id,)
        ).fetchone()[0]
        if status == "resolved" and pending:
            return {"ok": False, "message": f"Ticket {ticket_id} still has {pending} pending payment request(s); "
                                            "use waiting_on_human until a human decides."}
        draft_quotes = conn.execute(
            "SELECT COUNT(*) FROM quotes WHERE ticket_id = ? AND status = 'draft'", (ticket_id,)
        ).fetchone()[0]
        if status == "waiting_on_human" and not pending and not draft_quotes:
            return {"ok": False, "message": f"Nothing on ticket {ticket_id} is waiting for a human (no pending payment "
                                            "request, no draft quote). Either have Accounting prepare what the human "
                                            "must approve, or mark the ticket resolved."}
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        conn.execute(
            "INSERT INTO ticket_updates (ticket_id, old_status, new_status, note, updated_by, updated_at) VALUES (?,?,?,?,?,?)",
            (ticket_id, t["status"], status, note, updated_by, _stamp()),
        )
        return {"ok": True, "ticket_id": ticket_id, "old_status": t["status"], "new_status": status}


# --------------------------------------------------------------------------
# human-only tools: the backend never gives these to an agent
# --------------------------------------------------------------------------

@mcp.tool
def approve_payment_request(request_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Approve a pending payment / purchase-order request and
    actually move the money: checks cash, writes a payments row, lowers the
    checking balance, and updates the source (invoice -> paid, lease ->
    next_due moves one month). Refuses if cash would go negative, or if a
    purchase order's vendor still has an open invoice.

    Args:
        request_id: payment_requests.id
        approved_by: the human's name (required).
    """
    if not approved_by or not approved_by.strip():
        return {"ok": False, "message": "approved_by (a human's name) is required."}
    with _connect(write=True) as conn:
        r = conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if r is None:
            return {"ok": False, "message": f"No payment request {request_id}."}
        if r["status"] != "pending":
            return {"ok": False, "message": f"Request {request_id} is already {r['status']}."}

        today = _today(conn)
        if r["kind"] == "invoice":
            inv = conn.execute("SELECT status, amount FROM invoices WHERE id = ?", (r["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                return {"ok": False, "message": f"Invoice {r['ref_id']} is no longer open."}
            if inv["amount"] != r["amount"]:
                return {"ok": False, "message": "Invoice amount changed since the request was prepared; re-prepare it."}
        if r["kind"] == "purchase_order":
            blockers = _open_invoices(conn, r["vendor_id"])
            if blockers:
                return {"ok": False, "message": f"{r['payee']} still has open invoice(s) {[b['id'] for b in blockers]}; "
                                                "it will not ship. Pay those first."}

        balance = _checking(conn)
        if balance - r["amount"] < 0:
            return {"ok": False, "message": f"Not enough cash: checking has ${balance:.2f}, request is ${r['amount']:.2f}. "
                                            "Refused; balances never go negative.",
                    "checking_balance": balance}

        new_balance = round(balance - r["amount"], 2)
        pay = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?,?,?, 'checking', ?, ?)",
            (r["kind"], r["ref_id"] if r["ref_id"] is not None else r["id"], r["amount"], today, approved_by.strip()),
        )
        conn.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = 'checking'", (new_balance, today))
        source_update = None
        if r["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (r["ref_id"],))
            source_update = f"invoice {r['ref_id']} -> paid"
        elif r["kind"] == "rent":
            lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (r["ref_id"],)).fetchone()
            nxt = _add_month(lease["next_due"])
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (nxt, r["ref_id"]))
            source_update = f"lease {r['ref_id']} next_due {lease['next_due']} -> {nxt}"
        else:
            source_update = f"purchase order placed; {r['qty']} x {r['sku']} {r['size']} expected {r['expected_arrival']}"
        conn.execute(
            "UPDATE payment_requests SET status = 'approved', decided_by = ?, decided_at = ?, payment_id = ? WHERE id = ?",
            (approved_by.strip(), _stamp(), pay.lastrowid, request_id),
        )

        ticket_status = None
        if r["ticket_id"] is not None:
            left = conn.execute(
                "SELECT COUNT(*) FROM payment_requests WHERE ticket_id = ? AND status = 'pending'", (r["ticket_id"],)
            ).fetchone()[0]
            t = conn.execute("SELECT status FROM tickets WHERE id = ?", (r["ticket_id"],)).fetchone()
            if not left and t and t["status"] == "waiting_on_human":
                conn.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (r["ticket_id"],))
                conn.execute(
                    "INSERT INTO ticket_updates (ticket_id, old_status, new_status, note, updated_by, updated_at) VALUES (?,?,?,?,?,?)",
                    (r["ticket_id"], "waiting_on_human", "resolved",
                     f"Last pending request #{request_id} approved by {approved_by.strip()}.", approved_by.strip(), _stamp()),
                )
                ticket_status = "resolved"
        return {
            "ok": True, "request_id": request_id, "payment_id": pay.lastrowid,
            "amount": r["amount"], "payee": r["payee"],
            "balance_before": balance, "balance_after": new_balance,
            "source_update": source_update, "ticket_status": ticket_status,
        }


@mcp.tool
def reject_payment_request(request_id: int, decided_by: str, note: str = "") -> dict:
    """HUMAN ONLY. Reject a pending payment / purchase-order request. No
    money moves.
    """
    if not decided_by or not decided_by.strip():
        return {"ok": False, "message": "decided_by (a human's name) is required."}
    with _connect(write=True) as conn:
        r = conn.execute("SELECT status FROM payment_requests WHERE id = ?", (request_id,)).fetchone()
        if r is None:
            return {"ok": False, "message": f"No payment request {request_id}."}
        if r["status"] != "pending":
            return {"ok": False, "message": f"Request {request_id} is already {r['status']}."}
        conn.execute(
            "UPDATE payment_requests SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ? WHERE id = ?",
            (decided_by.strip(), _stamp(), note, request_id),
        )
        return {"ok": True, "request_id": request_id, "status": "rejected"}


@mcp.tool
def confirm_price_quote(quote_id: int, confirmed_by: str) -> dict:
    """HUMAN ONLY. Confirm a draft price quote, so the shop stands behind that
    price. No money moves. If the quote's ticket is waiting on a human and has
    nothing else pending (no pending payment requests, no other draft
    quotes), the ticket is marked resolved.
    """
    if not confirmed_by or not confirmed_by.strip():
        return {"ok": False, "message": "confirmed_by (a human's name) is required."}
    with _connect(write=True) as conn:
        q = conn.execute("SELECT * FROM quotes WHERE id = ?", (quote_id,)).fetchone()
        if q is None:
            return {"ok": False, "message": f"No quote {quote_id}."}
        if q["status"] != "draft":
            return {"ok": False, "message": f"Quote {quote_id} is already {q['status']}."}
        conn.execute("UPDATE quotes SET status = 'confirmed', note = COALESCE(note, '') || ? WHERE id = ?",
                     (f" [confirmed by {confirmed_by.strip()} {_stamp()}]", quote_id))
        tid = q["ticket_id"]
        pending = conn.execute("SELECT COUNT(*) FROM payment_requests WHERE ticket_id = ? AND status = 'pending'",
                               (tid,)).fetchone()[0]
        drafts = conn.execute("SELECT COUNT(*) FROM quotes WHERE ticket_id = ? AND status = 'draft'", (tid,)).fetchone()[0]
        t = conn.execute("SELECT status FROM tickets WHERE id = ?", (tid,)).fetchone()
        ticket_status = t["status"] if t else None
        if t and t["status"] == "waiting_on_human" and not pending and not drafts:
            conn.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (tid,))
            conn.execute(
                "INSERT INTO ticket_updates (ticket_id, old_status, new_status, note, updated_by, updated_at) VALUES (?,?,?,?,?,?)",
                (tid, "waiting_on_human", "resolved", f"Quote #{quote_id} confirmed by {confirmed_by.strip()}.",
                 confirmed_by.strip(), _stamp()),
            )
            ticket_status = "resolved"
        return {"ok": True, "quote_id": quote_id, "status": "confirmed", "ticket_id": tid,
                "ticket_status": ticket_status, "message": "Quote confirmed. No money moved."}


if __name__ == "__main__":
    mcp.run()
