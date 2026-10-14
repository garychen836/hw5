# HW 5 Harness — Campus Customs Multi-Agent Operations

This file describes everything the agent team works with. It grew problem by problem.

**Contents**
1. Database: tables, fields, links, starting values
2. The three open tickets and what they touch
3. MCP server: all 16 tools and the tables each uses
4. The agent team: the five agents, their tools, delegation, audit trail
5. Safety: guardrails for a real business, plus token limits
6. Backend routes
7. Dashboard
8. Graded run (Problem 9)

---

## 1. Database

- **Original:** `data/campus_customs.db` — never edited. It is the reset point for a clean run.
- **Working copy:** `data/campus_customs_new.db` — a byte-for-byte copy of the original (same SHA-1, `f447ca6a…`). The MCP server and backend read and write only this file.
- **To reset:** copy `campus_customs.db` over `campus_customs_new.db` again.

### Tables

Row counts are from the original file. Bold fields are primary keys.

| Table | Fields | Rows | Why it matters for the agents |
|---|---|---|---|
| `desk` | `date_today` TEXT, `notes` TEXT | 1 | The shop's "today" (2026-08-31); every agent uses it, not the real clock, to decide what is overdue or due soon. |
| `tickets` | **`id`** INTEGER, `type` TEXT, `requester` TEXT, `subject` TEXT, `sku` TEXT, `size` TEXT, `qty` INTEGER, `lease_id` INTEGER → leases, `invoice_id` INTEGER → invoices, `status` TEXT, `notes` TEXT, `created_at` TEXT | 3 | The Boss's work queue; the `type` and the filled-in link fields (`sku`/`size`/`qty`, `lease_id`, `invoice_id`) tell the Boss which specialist each ticket needs. |
| `inventory` | **`sku`** TEXT, `name` TEXT, **`size`** TEXT, `qty` INTEGER, `location` TEXT | 10 | Stock by SKU and size (key is the pair); Inventory uses it to find shortfalls such as the 0 white tees in S. |
| `pricing` | **`sku`** TEXT, `unit_cost` REAL, `list_price` REAL | 4 | Cost and price per SKU; Accounting uses it to check margin before agreeing to any discount and to price a restock purchase. |
| `vendors` | **`id`** INTEGER, `name` TEXT, `specialty` TEXT, `lead_days` INTEGER | 3 | Who can restock what and how many days it takes; the only allowed source for lead times. |
| `leases` | **`id`** INTEGER, `space_name` TEXT, `landlord` TEXT, `monthly_rent` REAL, `next_due` TEXT, `notes` TEXT | 1 | Facilities' table: rent amount and due date for the Chapel Street shop. |
| `cash_accounts` | **`name`** TEXT, `balance` REAL, `date` TEXT | 1 | The checking balance ($3,400.00); every pay must check it first and may never take it below zero. |
| `payments` | **`id`** INTEGER, `kind` TEXT, `ref_id` INTEGER, `amount` REAL, `account` TEXT, `paid_at` TEXT, `approved_by` TEXT | 0 | The record of money going out; `approved_by` (required) is the proof a human approved each pay. Empty at the start. |
| `invoices` | **`id`** INTEGER, `vendor_id` INTEGER → vendors, `amount` REAL, `due_date` TEXT, `status` TEXT, `description` TEXT | 1 | What the shop owes vendors; an `open` invoice blocks that vendor from shipping anything new. |

### How the tables link

- `tickets.invoice_id` → `invoices.id` → `invoices.vendor_id` → `vendors.id`
- `tickets.lease_id` → `leases.id`
- `tickets.sku` (+ `size`) → `inventory.sku` (+ `size`), and `tickets.sku` → `pricing.sku`. The schema does not enforce these as foreign keys, so joins are by matching values.
- `payments.ref_id` points at an invoice id or a lease id, depending on `payments.kind`. The schema does not enforce this either, so the pay tool must write `kind` correctly.
- `payments.account` → `cash_accounts.name` (only `checking` exists).

### Starting values (from the original file)

- **Today:** 2026-08-31.
- **Cash:** checking holds $3,400.00 (dated 2026-08-31).
- **Inventory:**
  - CC-HOOD-NAVY (Basic Hoodie Big Yale, Aisle A): S 4, M 8, L 14, XL 6
  - CC-TEE-WHITE (Classic Bulldog Tee, Aisle B): S 0, M 5, L 3, XL 2
  - CC-HAT-BLUE (Yale Cap, Aisle C): OS 40
  - CC-MUG-CREST (Crest Mug, Aisle D): OS 0
- **Pricing (cost → list):**
  - Hoodie $22 → $58
  - Tee $8 → $28
  - Cap $6 → $22
  - Mug $3.50 → $14
- **Vendors:**
  - 1 Bulldog Print Co (apparel reprint), 5 lead days
  - 2 Elm City Gifts (mugs and small goods), 3 lead days
  - 3 QuickShip CT (local courier), 1 lead day
- **Lease:** 1 Chapel Street shop, Elm City Properties, $2,400/month, next due 2026-09-02.
- **Invoice:** 501 to Bulldog Print Co, $840, due 2026-08-28, status `open`, "Rush reprint CC-TEE-WHITE S".
- **Payments:** none.

---

## 2. The three open tickets and what they touch

### Ticket 101 — customer order

- **From:** Tauhid Zaman, "Bulldog tee": wants 1 × CC-TEE-WHITE in size S.
- **Links:** the SKU, size and qty point to `inventory`, where S has qty **0**, so it can't be filled from stock. It also links `invoice_id` 501.
- **Invoice 501:** owed to vendor 1, Bulldog Print Co (apparel reprint, 5 lead days), $840 for a rush reprint of exactly this tee. Its due date, 2026-08-28, is before today (2026-08-31), so it is **3 days overdue** and still `open`.
- **Shop rule:** a vendor with an open unpaid invoice won't ship, so no new tees arrive until 501 is paid.
- **Tables:** tickets, inventory, invoices, vendors, pricing, cash_accounts, payments.

### Ticket 102 — rent notice

- **From:** Elm City Properties, "Rent due in 2 days." It links `lease_id` 1.
- **Lease 1:** the Chapel Street shop, $2,400, next due 2026-09-02, which is 2 days after today. Not overdue yet, but due before a typical vendor lead time would finish.
- **Tables:** tickets, leases, cash_accounts, payments.

### Ticket 103 — price override

- **From:** Yale AI Club, "Bulk hoodie discount": wants 20 × CC-HOOD-NAVY in size M at a bulk discount.
- **Stock:** inventory has only **8** in M, a shortfall of 12. Other sizes are S 4, L 14, XL 6.
- **Pricing:** cost $22, list $58, a $36 margin per hoodie. Any discount must be weighed against that margin.
- **Restock:** the apparel vendor is Bulldog Print Co (5 lead days), the same vendor blocked by unpaid invoice 501.
- **Tables:** tickets, inventory, pricing, vendors, invoices.

### Where the tickets collide

These are facts from the data, not plans.

- **101 and 103 both depend on invoice 501.** Bulldog Print Co is the only apparel vendor, so neither the S tee nor the extra M hoodies can be restocked until 501 is paid.
- **All three draw on one $3,400 checking balance:**
  - invoice 501: $840
  - rent: $2,400
  - after paying both: **$160** left
- **A restock purchase may not fit.** At unit cost, 12 M hoodies would be 12 × $22 = $264, which is more than $160. So the order of payments, and which ones a human approves, matters. The pay tool must refuse anything that would push the balance negative.

---

## 3. MCP server

- **Code:** `mcp_server/server.py`, built with FastMCP, server name `campus-customs`.
- **Database:** only `data/campus_customs_new.db`. The three starting tools use a read-only connection; write tools are added in Problem 5.
- **Who uses it:** every agent built in Problem 5 gets shop facts from these tools and nowhere else.

**Anti-invention rules, enforced in code:**
- A missing id returns `"found": false` with a message, not a made-up row.
- "Today" comes from `desk.date_today`, never the system clock.
- Shortfalls, margins and day counts are computed in Python, not left to the model.

### The three starting tools

Each tool unlocks one ticket, so all three tickets are covered.

| Tool | Tables it reads | Ticket it unlocks | What it returns for that ticket (values from the original DB) |
|---|---|---|---|
| `get_invoice_status(invoice_id)` | `invoices`, `vendors`, `desk` | **101** | For invoice 501: $840, due 2026-08-28, `open`, 3 days overdue as of 2026-08-31. Vendor Bulldog Print Co (apparel reprint, 5 lead days), 1 open invoice, `vendor_will_ship` false |
| `get_lease_status(lease_id)` | `leases`, `desk` | **102** | For lease 1: Chapel Street shop, Elm City Properties, $2,400, due 2026-09-02, 2 days until due, not overdue |
| `check_stock(sku, size, qty_needed)` | `inventory`, `pricing` | **103** | For CC-HOOD-NAVY, size M, qty 20: on hand 8, shortfall 12, `can_fill_from_stock` false, other sizes S 4 / L 14 / XL 6, cost $22 / list $58 / margin $36 |

### Why each tool is the right one for its ticket (one sentence each)

- **`get_invoice_status` → ticket 101:** Tauhid Zaman's size-S tee is at 0 and ticket 101 links invoice 501, so this tool is the one that shows the $840 owed to Bulldog Print Co is 3 days past due (counted from `desk.date_today`) and returns `vendor_will_ship: false`, which proves the tee can't be restocked until a human approves paying that invoice.
- **`get_lease_status` → ticket 102:** The rent ticket is only Elm City Properties' email saying "rent due in 2 days," so this tool checks that claim against lease 1 itself ($2,400, due 2026-09-02, exactly 2 days from shop today) before anyone prepares a rent payment.
- **`check_stock` → ticket 103:** The Yale AI Club wants 20 navy hoodies in M at a discount, and this one call returns both facts that decide the answer: only 8 are on the shelf (12 short), and the margin a discount would eat into is $36 per hoodie ($58 list − $22 cost).

**Reuse on the other tickets:**
- `check_stock` also confirms 101's shortfall: CC-TEE-WHITE size S shows 0 on hand, with M 5 / L 3 / XL 2 as real alternatives.
- `get_invoice_status` also explains why 103's 12 missing hoodies can't be reprinted yet: the only apparel vendor is blocked by invoice 501.

### All MCP tools (Problem 5)

Sixteen tools. The first three are from Problem 3; the rest were added so the team can work the open tickets (`confirm_price_quote` was added in Problem 7).

**Read tools** (read-only connection):

| Tool | Tables it uses | What it is for |
|---|---|---|
| `list_tickets(status?)` | `tickets`, `desk` | The Boss's queue: id, type, requester, subject, status |
| `get_ticket(ticket_id)` | `tickets`, `desk`, `payment_requests`, `quotes`, `message_drafts`, `ticket_updates` | One ticket in full, plus everything already prepared for it, so nobody duplicates work |
| `check_stock(sku, size, qty_needed)` | `inventory`, `pricing` | On hand, shortfall, other sizes, cost / list / margin (101, 103) |
| `find_vendors(specialty_keyword?)` | `vendors`, `invoices`, `desk` | Who can restock, lead days, earliest arrival, and `will_ship` (blocked by open invoices) |
| `get_invoice_status(invoice_id)` | `invoices`, `vendors`, `desk` | Amount, days overdue, vendor blocked or not (101) |
| `get_lease_status(lease_id)` | `leases`, `desk` | Rent, next due, days until due (102) |
| `get_cash_balance()` | `cash_accounts`, `payment_requests`, `payments`, `desk` | Balance now, total pending, and balance if every pending request were approved |
| `list_payment_requests(status?, ticket_id?)` | `payment_requests` | What is waiting for a human |

**Write tools agents may use.** None of these moves money or contacts anyone:

| Tool | Tables it uses | What it does |
|---|---|---|
| `prepare_payment(kind, ref_id, ticket_id, ...)` | reads `invoices` / `vendors` or `leases`, `cash_accounts`; writes `payment_requests` | Prepares an invoice or rent payment. The amount and payee come from the database row, never from the agent. Refuses duplicates and invoices that are not open |
| `prepare_purchase_order(sku, size, qty, vendor_id, ...)` | reads `pricing`, `inventory`, `vendors`, `invoices`, `cash_accounts`; writes `payment_requests` | Prepares a restock. Cost = qty × unit_cost; arrival = today + lead_days. Flags a vendor blocked by an open invoice. Refuses an order costing more than the whole checking balance (no money ever comes in) |
| `prepare_price_quote(ticket_id, sku, size, qty, discount_pct, ...)` | reads `pricing`, `inventory`; writes `quotes` | Draft discount quote with margin math. Refuses anything at or below cost (103) |
| `draft_customer_message(ticket_id, recipient, subject, body, ...)` | reads `tickets`; writes `message_drafts` | Saves a draft on the board. Never sent |
| `update_ticket_status(ticket_id, status, note, ...)` | `tickets`, `ticket_updates`, `payment_requests`, `quotes` | open → in_progress → waiting_on_human / resolved. Refuses `resolved` while a payment request is pending, and `waiting_on_human` when nothing is actually waiting |

**Human-only tools.** No agent can reach these; they are for the dashboard's approve button:

| Tool | Tables it uses | What it does |
|---|---|---|
| `approve_payment_request(request_id, approved_by)` | `payment_requests`, `cash_accounts`, `payments`, `invoices` / `leases`, `vendors`, `tickets`, `ticket_updates` | Requires a human name. Re-checks the source and refuses if cash would go negative, or if a purchase order's vendor still has an open invoice. Then, in one transaction: writes `payments` (with `approved_by`), lowers checking, and updates the source (invoice → `paid`; lease `next_due` + 1 month). Marks the ticket `resolved` when its last pending request is approved |
| `reject_payment_request(request_id, decided_by, note)` | `payment_requests` | Rejects a request. No money moves |
| `confirm_price_quote(quote_id, confirmed_by)` | `quotes`, `payment_requests`, `tickets`, `ticket_updates` | A human confirms a draft quote (ticket 103). No money moves. Resolves the ticket if nothing else is pending |

**Tables the server adds to the working copy.** They are created on first write, so a reset to the original starts them empty:
- `payment_requests`
- `quotes`
- `message_drafts`
- `ticket_updates`

---

## 4. The agent team (Problem 5)

- **Framework:** PydanticAI.
- **Model:** every agent uses **gpt-6-luna** only, built once in `backend/llm.py`. Calls go to OpenAI with my own `OPENAI_API_KEY`; the course Portkey key hit its usage cap during this homework, so it is not used.
- **Prompts:** in `backend/prompts/`, one file per agent.
- **Agent files:** in `backend/agents/`.
- **Data types:** in `backend/models.py`.
- **Shop facts:** every agent gets them only from the MCP server above, over stdio. There is no other shop-tools layer.

| Agent | File / prompt | Job | MCP tools it may call | Returns |
|---|---|---|---|---|
| **Boss** | `agents/boss.py`, `prompts/boss.md` | Reads each ticket, decides who works on it, makes the final call, sets the ticket status | `list_tickets`, `get_ticket`, `get_cash_balance`, `list_payment_requests`, `update_ticket_status` | `TicketResolution` |
| **Inventory** | `agents/inventory.py`, `prompts/inventory.md` | Controls stock: on hand by SKU and size, shortfalls, alternatives, which vendor can restock and when | `get_ticket`, `check_stock`, `find_vendors`, `get_invoice_status` | `AgentReport` |
| **Accounting** | `agents/accounting.py`, `prompts/accounting.md` | Keeps money clear: cash, invoices, margins; prepares payments, purchase orders and quotes for human approval | `get_ticket`, `get_cash_balance`, `list_payment_requests`, `get_invoice_status`, `get_lease_status`, `check_stock`, `find_vendors`, `prepare_payment`, `prepare_purchase_order`, `prepare_price_quote` | `AgentReport` |
| **Facilities** | `agents/facilities.py`, `prompts/facilities.md` | Monitors the shop space: checks the lease, rent and due date against the landlord's notice | `get_ticket`, `get_lease_status`, `get_cash_balance` | `AgentReport` |
| **Customer Service** | `agents/customer_service.py`, `prompts/customer_service.md` | Handles customers kindly, assumes good will, drafts honest messages; never sends, never shares costs | `get_ticket`, `check_stock`, `draft_customer_message` | `AgentReport` |

The allow-lists live in `backend/agents/mcp.py` (`ALLOWED_TOOLS`). Every agent also has `ask_teammate`.

### How they delegate (full connectivity)

- **Any agent can ask any other.** Every agent has `ask_teammate(teammate, task)`, which runs that teammate's own agent loop and hands back its report. The report also lists `agents_involved`, so onward handoffs are visible to the caller. In the test run on ticket 102, for example, Boss → Facilities → Accounting.
- **Loop guards, enforced in code** (`agents/base.py`). A delegation is refused, and the refusal is logged, if:
  - an agent asks itself
  - the teammate is already waiting on the current chain (A → B → A)
  - the chain would be deeper than 3
  - the ticket has used 10 delegations
  - fewer than 6,000 tokens are left
- **The agent loop.** Each agent runs PydanticAI's `agent.iter()`: model request → tool calls → tool results → … → structured output. A ticket run (`backend/team.py`, `run_ticket`) opens the MCP server once, starts the Boss, and lets delegations nest. Only one ticket runs at a time, because all tickets share one checking account.

### Audit trail (`output/audit_trail.json`)

`backend/audit.py` appends one entry per agent-loop step to a JSON array. Old entries are never removed, so new runs add on and nothing is wiped. Every entry has:
- `seq` (unique)
- `ts`
- `run_id`
- `ticket_id`
- `agent`
- `chain` (e.g. `boss > facilities > accounting`)
- `event`

Events:
- `run_start`: model, which key, database, limits
- `agent_start`: the task given
- `model_step`: step number, tokens (input / cached / output), text, tool calls with arguments
- `tool_result`: tool name and result, clipped at 2,000 characters
- `handoff`: from, to, task
- `delegation_refused`: reason
- `limit_hit` / `agent_error`
- `agent_done`: the agent's structured output
- `run_end`: status, every handoff, token usage per agent and in total

---

## 5. Safety: guardrails for a real business

Most of these rules are enforced in code, not only asked for in a prompt.

**Money**
- **No agent can move money.** Agents can only *prepare* requests. `approve_payment_request` (and the other human-only tools, `reject_payment_request` and `confirm_price_quote`) are on no agent's allow-list, and the MCP call hook (`agents/mcp.py`) refuses it even if a model names it. Cash changes only when a named human approves on the dashboard.
- **Amounts come from the database, never from the model.** `prepare_payment` reads the invoice or lease, `prepare_purchase_order` uses `pricing.unit_cost`, and `prepare_price_quote` does the discount math. A model cannot type in "$84" instead of "$840".
- **No negative cash.** Approval re-checks the live balance and refuses if it would go below zero. `get_cash_balance` and every prepare tool also show the balance if every pending request were approved, so overcommitting is visible early. (Example: invoice $840 + rent $2,400 leaves $160, so a $264 restock would be refused.)
- **The vendor rule is in code.** A purchase order to a vendor with an open invoice can be prepared, but cannot be approved until that invoice is paid.
- **Approval re-checks the source.** It refuses if the invoice is no longer open or its amount changed since the request was prepared, so a stale request can't pay the wrong number.
- **No double payments.** A second pending request for the same invoice or lease is refused.
- **Every payment has a name on it.** Each `payments` row records `approved_by`.

**Customers and outsiders**
- Nothing is sent. Customer messages are drafts on the board, and no tool can email or call anyone.
- Customer Service is told never to share costs, margins, cash or vendor problems with a customer, and never to promise a date or discount the tools did not give.

**Least power and honest records**
- Each agent sees only the tools its job needs. For example, the Boss cannot prepare payments and Customer Service cannot quote prices.
- The hook stamps the real agent name into `requested_by` / `prepared_by` / `written_by` / `updated_by`, so the database shows who actually acted.
- "Today" is `desk.date_today`, never the clock.
- Missing data returns `"found": false` instead of a guess.
- A ticket cannot be marked resolved while one of its payments is still pending.
- Only one ticket runs at a time, and the original database is never opened by the server.

**What a real shop would add**
- Approval limits by amount, so large payments need two people.
- A login on the approve button.
- Daily spend caps.
- Separate vendor bank-detail checks.
- Encrypted customer data.

### Limits that keep token use in check

| Limit | Value | Where |
|---|---|---|
| Model | gpt-6-luna only (cheapest course model), reasoning off | `backend/llm.py` |
| Team token budget per ticket run | 120,000 tokens, shared by all agents | `models.Budget`, passed as `UsageLimits.total_tokens_limit` |
| Model requests per agent run | Boss 12, specialists 8 | `agents/base.py` `REQUEST_LIMITS` |
| Output tokens per response | 1,200 | `agents/base.py` `MAX_OUTPUT_TOKENS` |
| Delegations per ticket | 10 | `models.Budget.max_delegations` |
| Delegation depth | 3 | `models.Budget.max_depth` |
| Loop prevention | No self-delegation and no asking back up the chain | `ask_teammate` |
| Prompt caching | Each agent's system prompt is fully static (run facts go in the task message), so the provider caches it | `agents/base.py` |
| Tool results | Computed in code and compact. The Boss is told not to send every specialist to every ticket | `prompts/boss.md` |

**Measured** (test runs, 2026-10-13/14, all three tickets): 13–17 model requests and about 31k–41k input tokens per ticket. **69–87% of input tokens were cached** after the static-prompt fix (101: 28,250 / 40,850; 102: 25,956 / 31,065; 103: 28,333 / 32,693; the real run on 102: 31,205 / 36,962), against 0% before it. Output was about 1.1k–1.7k tokens per ticket.

---

## 6. Backend routes (Problem 7)

**File:** `backend/main.py` (FastAPI).
**Start it:** from `backend/`, run `uvicorn main:app --reload --port 8000` (using the project `.venv`). It serves `http://localhost:8000` and allows the React board's origin `http://localhost:5173` (CORS).

**How it reaches the data:** every route goes through the same Campus Customs MCP tools the agents use (an in-process MCP session), so the API has no back door into the database. The human routes call the human-only MCP tools. They require a person's name and refuse agent names like "Boss" or "accounting".

| Method | URL | What it does |
|---|---|---|
| GET | `/api/tickets` | The three tickets, each `open` or `resolved` (plus the detailed status), with pending payments, draft quotes and message drafts |
| GET | `/api/tickets/{ticket_id}` | One ticket in full: fields, payment requests, quotes, drafts, status history |
| POST | `/api/tickets/{ticket_id}/run` | Starts the agent team on that ticket in the background and returns a `run_id` at once. Refused (409) if another run is going, because tickets share one cash account |
| GET | `/api/events?since=&run_id=` | Recent agent events, newest last, so the board can refresh: what each agent said, which tools it called, handoffs, results. Pass the last `seq` seen as `since` |
| GET | `/api/runs/{run_id}` | A run's status, the Boss's resolution, and per-agent outputs and tools used, plus handoffs and token use (per-agent summary for the board) |
| GET | `/api/runs` | Every run recorded in the audit trail |
| GET | `/api/payments?status=pending` | Payment and purchase-order requests the agents prepared |
| POST | `/api/payments/{request_id}/approve` | **Human only.** The one route that changes cash: pays a prepared request after a person clicks approve (body `{"name": "Gary Chen"}`). Refuses agent names, duplicate approvals, negative cash, and purchase orders whose vendor still has an open invoice |
| POST | `/api/payments/{request_id}/reject` | **Human only.** Rejects a prepared request; no money moves |
| POST | `/api/quotes/{quote_id}/confirm` | **Human only.** Confirms a draft price quote (ticket 103); no money moves; resolves the ticket if nothing else is pending |
| POST | `/api/tickets/{ticket_id}/resolve` | **Human only.** A person marks a ticket resolved; refused while a payment on it is pending |
| GET | `/api/cash` | The current checking balance from `cash_accounts`, plus pending requests and the balance if all of them were approved |
| POST | `/api/reset` | Copies the original `data/campus_customs.db` over `data/campus_customs_new.db` for a fresh run. Refused during a run. The audit trail is kept, and a `db_reset` entry is added |
| GET | `/api/health` | Model (gpt-6-luna), which key is in use, which database, and whether a run is active |

**Every human action is in the audit trail too:** approvals, rejections, quote confirmations, manual resolves and resets each append a `human_action` or `db_reset` entry to `output/audit_trail.json`, recording who did it and the outcome.

**Tested** end to end on a scratch copy of the database (2026-10-14), through the API, with real gpt-6-luna runs:

| Step | What happened | Checking |
|---|---|---|
| Reset | Database restored to the original | $3,400.00 |
| Run 101 | Boss → Inventory → Accounting prepared #1 ($840); Customer Service drafted a reply to Tauhid Zaman | |
| Approve #1 | A human approved the $840; invoice 501 → paid; ticket 101 resolved | $2,560.00 |
| Run 102 | Boss → Facilities → Accounting prepared #2 ($2,400 rent) | |
| Approve #2 | A human approved the rent; lease `next_due` → 2026-10-02; ticket 102 resolved | $160.00 |
| Run 103 | Boss → Inventory, Accounting (10% quote at $52.20) and Customer Service (offer to the Yale AI Club). No unaffordable restock | |
| Confirm quote #1 | A human confirmed the quote; ticket 103 resolved | $160.00 |

All three tickets ended resolved at $160.00. These were also refused:
- approving as "Boss"
- approving the same request twice
- starting a second run, or resetting, while a run was going
- (in an earlier test) a $264 restock with only $160 in checking

**Fixes made during testing:**
- **Stale key:** the app environment carried an old, capped course key. `backend/llm.py` now reads the API key only from the project `.env` when it exists, and uses only `OPENAI_API_KEY`.
- **False "waiting" status:** the Boss could mark a ticket `waiting_on_human` with nothing pending. The status tool now refuses that.
- **Agent behaviour:** prompts now have Inventory hand invoice blockers to Accounting itself, call Customer Service last with the facts, require a reply to every customer, and stop a second purchase order when an open invoice already covers the item.

---

## 7. Dashboard (Problem 8)

- **What it is:** a React + Vite + TypeScript board in `frontend/`. Start it with `npm run dev` and open http://localhost:5173. It calls the backend directly at `http://localhost:8000`, and the backend's CORS allows the Vite origin.
- **Design:** the full write-up is in `output/design.md`.
- **Layout:**
  - **Ticket rail:** the three tickets as order slips, each with an Open → Team at work → Your call → Resolved stepper, a RESOLVED stamp, and a Run button.
  - **Shop floor:** five agent stations with sticker dogs, live speech bubbles and a handoff trail; agent-to-agent handoffs are in orange.
  - **Live feed:** what each agent said and which MCP tools it called, with expandable results.
  - **What each agent did:** the Boss's call plus one card per agent.
  - **Needs you:** approve or reject payments, confirm quotes, close tickets, read drafts. A typed human name is required.
  - **Till:** the checking balance, which counts down after an approved pay.
- **Data:** every value on the board comes from the API, and so through the MCP server; nothing is hard-coded.
- **Tested in the browser** on a scratch copy of the database (2026-10-14), with real gpt-6-luna runs:
  - **Ticket 101:** run from the board, it followed the plan exactly (Boss → Inventory → Accounting, Boss → Customer Service). Approving $840 dropped the till from $3,400.00 to $2,560.00 and stamped 101 resolved.
  - **Ticket 103:** a 10% quote and a draft to the Yale AI Club. Confirming the quote resolved it.
  - **Reset:** restored $3,400.00 and 0/3 resolved.
  - No console errors.

---

## 8. Graded run (Problem 9)

**Setup:** on 2026-10-14 the working database was reset from the original (audit entry #99). Then tickets 101 → 102 → 103 were each started from the React board and resolved after a human approval, signed "Gary Chen". The runs are appended to `output/audit_trail.json` from entry #99 onward.

| Ticket | Boss called first | Handoffs | Human approval | Cash | Tokens in (cached) |
|---|---|---|---|---|---|
| 101 | Inventory | Boss→Inventory, Boss→Accounting, **Inventory→Accounting**, Boss→Customer Service | Paid invoice #501, $840 | $3,400 → $2,560 | 58,078 (86%) |
| 102 | Facilities | Boss→Facilities, Boss→Accounting | Paid rent, $2,400 | $2,560 → $160 | 37,653 (89%) |
| 103 | Inventory | Boss→Inventory, Boss→Accounting, Boss→Customer Service | Confirmed quote #1 (10% off) | $160 → $160 | 52,775 (87%) |

**Ending checking balance: $160.00.** That matches `cash_accounts` in `data/campus_customs_new.db`. The math is $3,400 − $840 − $2,400 = $160.

**Evidence:**
- `output/desk_tickets.html`: the Actual sections and the Cash tab
- `output/resolved_tickets.json`
- `output/resolved_board.html`
- `output/screenshots/board_101.png`, `board_102.png`, `board_103.png`
