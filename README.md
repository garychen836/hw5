# Campus Customs Multi-Agent Operations (MGT 409 · HW 5)

A five-agent team runs the Campus Customs shop: **Boss, Inventory, Accounting, Facilities and Customer Service**. Open tickets (a customer order, a rent notice, a bulk-discount request) land on a desk board. The agents work them through an **MCP server** over the shop database, and a human approves every payment on a **React dashboard**.

| Piece | Where | What it is |
|---|---|---|
| MCP server | `mcp_server/server.py` | FastMCP, 16 tools over `data/campus_customs_new.db`. The only way agents touch shop data |
| Agent team + API | `backend/` | PydanticAI agents (prompts in `backend/prompts/`), FastAPI routes in `backend/main.py` |
| Dashboard | `frontend/` | React + Vite + TypeScript board at http://localhost:5173 |
| Write-ups | `output/` | `harness.md`, `desk_tickets.html`, `design.md`, results, audit trail |

**Model:** every agent runs on **gpt-6-luna** only. The model name is fixed in `backend/llm.py`. Calls go to OpenAI with your own `OPENAI_API_KEY`. (The course Portkey key hit its usage cap during this homework, so it isn't used.)

**Safety:** agents only *prepare* payments. Cash changes only when a person clicks **Approve** on the board; see `output/harness.md` §5.

---

## 1 · Set up (once)

You need Python 3.11+ and Node 20+.

```bash
# from the repo root
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # then put your OpenAI key in .env:  OPENAI_API_KEY=sk-...

cd frontend && npm install && cd ..
```

`.env` stays on your machine. It is in `.gitignore` and is never committed.

## 2 · Copy the original database to the working copy (for a clean run)

`data/campus_customs.db` is the **original** and is never edited. Everything (the MCP server, the agents, the backend) reads and writes the **working copy**, `data/campus_customs_new.db`.

Whenever you want a clean start, copy the original over the working copy:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

(The board's **Reset database** button, or `POST /api/reset`, does the same thing.)

> The `campus_customs_new.db` in this repo is the **end state of the graded run**: tickets 101–103 resolved, checking at $160.00. Reset it before running the tickets yourself.

## 3 · Start the MCP server

The backend starts the MCP server for you, as a stdio subprocess (`mcp_server/server.py`), so the app works without this step. To run it on its own, or to check its tools:

```bash
cd mcp_server
../.venv/bin/python server.py
```

To use it from Claude Code, open this folder in Claude Code. `.mcp.json` registers it as `campus-customs`, and its tools show up as `mcp__campus-customs__*`.

## 4 · Start the FastAPI backend

In a new terminal, from the `backend/` folder, with the venv active:

```bash
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000
```

The backend serves http://localhost:8000. It allows the board's origin `http://localhost:5173`. Check it with http://localhost:8000/api/health, which shows `"model": "gpt-6-luna"` and `"key_source": "openai"`. All routes are listed in `output/harness.md` §6.

## 5 · Start the React board

In another terminal:

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. Type your name in "Signed in at the desk as" (approvals need a human name), pick a ticket on the rail, and press **Run the team**.

## 6 · A full three-ticket run

1. **Reset the database first:** `cp data/campus_customs.db data/campus_customs_new.db`, or click **Reset database** on the board. Checking should read **$3,400.00** and all three tickets should be **Open**.
2. Run **#101**. When the team finishes, approve the $840 invoice in **Needs you**. Checking goes to $2,560.00 and #101 is resolved.
3. Run **#102**. Approve the $2,400 rent. Checking goes to $160.00.
4. Run **#103**. Confirm the 10% quote; no money moves. All three are resolved.

Every step is appended to `output/audit_trail.json`. One run at a time: the board locks while a run is going, because the tickets share one cash account.

---

## Repo layout

```
.
├── AI_prompts.md            my prompts to the vibe coder, by problem
├── README.md
├── requirements.txt
├── .env.example             copy to .env and add OPENAI_API_KEY (the real .env is never committed)
├── .gitignore
├── .mcp.json                Claude Code connection to the MCP server
├── data/
│   ├── campus_customs.db        original (never edited)
│   └── campus_customs_new.db    working copy (end state of the graded run)
├── mcp_server/
│   ├── server.py            FastMCP server, 16 tools
│   └── README.md
├── backend/
│   ├── main.py              FastAPI routes
│   ├── models.py            data types (AgentReport, TicketResolution, Budget, TeamDeps)
│   ├── llm.py               gpt-6-luna model (the one place the model is set)
│   ├── team.py              run_ticket(): Boss first, specialists as delegated
│   ├── audit.py             append-only audit trail
│   ├── agents/              boss, inventory, accounting, facilities, customer_service + shared loop/MCP wiring
│   └── prompts/             boss.md, inventory.md, accounting.md, facilities.md, customer_service.md
├── frontend/                React + Vite + TypeScript board
├── assets/agent_stickers.jpg  sticker sheet used for the agent figures
└── output/
    ├── harness.md           tables, MCP tools, agents, safety, routes, dashboard, graded run
    ├── mcp_smoke.json       Problem 4 tool tests
    ├── desk_tickets.html    Expected / Actual per ticket + Cash + Reflection
    ├── design.md            dashboard design
    ├── resolved_tickets.json
    ├── resolved_board.html  board screenshots of the resolved tickets
    ├── screenshots/         full-size board screenshots
    ├── audit_trail.json     every agent-loop step (append-only)
    └── github_url.txt
```
