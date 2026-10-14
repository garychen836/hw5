# Campus Customs MCP server

**What it is for:** this is the one place the Campus Customs agent team gets shop facts and records its work. Every agent (Boss, Inventory, Accounting, Facilities, Customer Service) calls these tools instead of touching the database itself. That way all agents see the same numbers, and nobody makes data up.

**Database:** `data/campus_customs_new.db`, the working copy. The original `data/campus_customs.db` is never opened here; it is kept untouched for resets. To point at a different file, set the `CAMPUS_DB` environment variable.

**Built with:** [FastMCP](https://gofastmcp.com), over the stdio transport.

## Rules all tools follow

- Only report what is in the database. A missing id returns `"found": false` (or `"ok": false`) with a message, never a guess.
- "Today" is `desk.date_today` (2026-08-31 in the original data), not the computer clock.
- Day counts and money math (shortfalls, margins, days overdue, payment amounts) are done in code. Amounts always come from the invoice, lease or pricing row; a caller cannot set them.
- **No agent tool moves money.** Agents only *prepare* requests. Cash moves only in `approve_payment_request`, which is for a human; the human-only tools (`approve_payment_request`, `reject_payment_request`, `confirm_price_quote`) are given to no agent, and the backend's human routes are the only callers.
- **Nothing is sent anywhere.** Customer messages are saved as drafts.

## Tools (16)

### Read

| Tool | Tables | Returns |
|---|---|---|
| `list_tickets(status?)` | `tickets`, `desk` | The board: id, type, requester, subject, status |
| `get_ticket(ticket_id)` | `tickets` + the four added tables | One ticket in full, plus its payment requests, quotes, drafts and status history |
| `check_stock(sku, size, qty_needed)` | `inventory`, `pricing` | On hand, shortfall, every size's count, cost, list price, margin |
| `find_vendors(specialty_keyword?)` | `vendors`, `invoices`, `desk` | Specialty, lead days, earliest arrival, open invoices, `will_ship` |
| `get_invoice_status(invoice_id)` | `invoices`, `vendors`, `desk` | Amount, due date, status, days overdue, vendor, `vendor_will_ship` |
| `get_lease_status(lease_id)` | `leases`, `desk` | Space, landlord, rent, next due, days until due, overdue or not |
| `get_cash_balance()` | `cash_accounts`, `payment_requests`, `payments` | Balance, pending total, balance if all pending were approved |
| `list_payment_requests(status?, ticket_id?)` | `payment_requests` | Requests waiting for (or decided by) a human |

### Write: agents may use these; none moves money

| Tool | Tables | Does |
|---|---|---|
| `prepare_payment(kind, ref_id, ticket_id, requested_by, reason)` | `invoices`/`leases` → `payment_requests` | Prepares an invoice or rent payment for approval |
| `prepare_purchase_order(sku, size, qty, vendor_id, ticket_id, requested_by, reason)` | `pricing`, `vendors`, `invoices`, `cash_accounts` → `payment_requests` | Prepares a restock; flags a vendor blocked by an open invoice; refuses an order bigger than the whole balance |
| `prepare_price_quote(ticket_id, sku, size, qty, discount_pct, prepared_by, note)` | `pricing`, `inventory` → `quotes` | Draft discount quote; refuses at or below cost |
| `draft_customer_message(ticket_id, recipient, subject, body, written_by)` | `tickets` → `message_drafts` | Saves a draft; never sends |
| `update_ticket_status(ticket_id, status, note, updated_by)` | `tickets`, `ticket_updates` | Changes status; refuses `resolved` while a payment is pending, and `waiting_on_human` when nothing is waiting |

### Human only: never given to an agent

| Tool | Tables | Does |
|---|---|---|
| `approve_payment_request(request_id, approved_by)` | `payment_requests`, `cash_accounts`, `payments`, `invoices`/`leases`, `tickets` | Pays: refuses if cash would go negative or a PO's vendor still has an open invoice. Otherwise writes `payments`, lowers checking, marks the invoice paid or moves rent's `next_due` one month |
| `reject_payment_request(request_id, decided_by, note)` | `payment_requests` | Rejects; no money moves |
| `confirm_price_quote(quote_id, confirmed_by)` | `quotes`, `tickets` | Confirms a draft quote; no money moves; resolves the ticket if nothing else is pending |

**Tables added to the working copy** (created on first write; a reset starts them empty):
- `payment_requests`
- `quotes`
- `message_drafts`
- `ticket_updates`

## Run it

From `mcp_server/`:

```bash
../.venv/bin/python server.py
```

The agent backend starts it automatically (stdio), and Claude Code connects to it through `.mcp.json` at the project root.
