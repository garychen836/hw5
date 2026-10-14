# HW 5 AI Prompt Log

This file records the prompts I typed to my vibe coder for HW 5 (Campus Customs Multi-Agent Operations: an MCP server, a FastAPI backend with a five-agent PydanticAI team, and a React dashboard). Each problem has its own section with the problem number and title. Inside each section, every prompt is its own numbered entry, labeled as the **first prompt**, a **follow-up prompt** (with one sentence on what was lacking after the prompt before it), an **additional prompt**, or a **sanity check**. Prompts are copied word for word (typos included); screenshots I attached are described in brackets.

---

## Setup — Scenario, data, and environment

### Prompt 1 — Start the homework

> ok, lets do HW5

### Prompt 2 — Build the environment first

> ok you have the context, don't start yet, build the enviroment you need first — [screenshots of the Scenario and data section: Scenario, Data, and Rules of this shop]

### Prompt 3 — Continue

> proceed

### Prompt 4 — Swap in a new API key

> open up the env, i need to put in a new apikey

(When asked which editor to open it in, I answered: "yourself".)

### Prompt 5 — Key saved

> done, save it

### Prompt 6 — Lock the model

> make that a harness, use only gpt-luna as the agent

### Prompt 7 — Recheck the environment

> ok recheck the setting and environment, migrate necessary stuff from previous HWs if necessary

### Prompt 8 — Move everything into the HW 5 project (typed after Problem 4)

> ok, migrate all the stuff related to HW5, and from now on we stick there

---

## Problem 1 — Vibe coder prompts

### Prompt 1 (first prompt)

> ok let's start. Problem 1, create a AI_prompt.md file to log and update my prompts. make sure the prompt record each problem as each section. Make sure the problem number and titles are there, and it capture all the prompts i give you

### Prompt 2 (sanity check)

> btw, sanity check for P1 P2 and P3 — [screenshots of Problem 1 Panels A and B, Problem 2 Panels A and B, and Problem 3 Panels A and B]

**Result:** Nothing was lacking. The file is named `AI_prompts.md`, has one section per problem with its number and title, and logs every prompt word for word.

---

## Problem 2 — Study the Campus Customs database

### Prompt 1 (first prompt)

> ok P2. find the data i just downloaded in the download folder, migrate it to our HW folder. open the campus_customs.db, go through t. Copy the original file to a new file, campus_customs_new.db. lets work on that copy. study the open tickets and see the relationships there. start the harness.md under output folder (we mentioned this already). For each table, make susre you put all the fields and one short line for why each table matters for the agents.

### Prompt 2 (sanity check)

> btw, sanity check for P1 P2 and P3 — [screenshots of Problem 1 Panels A and B, Problem 2 Panels A and B, and Problem 3 Panels A and B]

**Result:** Nothing was lacking. Both database files exist, the copy matches the original byte for byte, and every table is listed with all its fields and a one-line reason.

---

## Problem 3 — Build the MCP server

### Prompt 1 (first prompt)

> ok P3, build the MCP server with three tools. Lets use FastMCP and have it talk to the new campus customs file we created. Make sure for the agents we are going to create later, they all use the tools in this MCP server. More tools will be added. Write now just include the tools you know you will need for the tickets here. Keep the names understandable and clear. Don't invent anydata (harness), to prevent hallucination. Only stick to the info from the database. In harness, list the MCP tools. for every tool, please include which table it reads, which ticket it helped, basically, functions. And one sentence to explain why each tool is the right solution for each situation. Be specific, Vague lines like "reads inventory" will have low socres. Make sure the tool ties to the tickets. Also add a readme file that explain what the MCP is for and which database it pulled and the tools.

### Prompt 2 (follow-up prompt, sanity check)

> btw, sanity check for P1 P2 and P3 — [screenshots of Problem 1 Panels A and B, Problem 2 Panels A and B, and Problem 3 Panels A and B]

**What was lacking:** The harness gave each tool several sentences instead of one, and it tied two tools to ticket 101 and none mainly to 103, so it was rewritten as one sentence per tool with each tool unlocking a different ticket (invoice → 101, lease → 102, stock → 103).

---

## Problem 4 — Add the MCP server to vibe coder and test each tool

### Prompt 1 (first prompt)

> ok P4, add the MCP server to this project so you can call the tools. Save the connection JSON text in the .mcp.json at the project root. Make sure you can call it. Oh btw, make sure in prompt, P1-3's name/title are recorded. keep on p4, write the connection, test each of the three MCP tools, save the evidence in the mcp_smoke.json. for every tool, make sure you have 1. the prompt you asked the vibe coder. 2. the tool name. 3. the tool output (must have value match in the campus customs new file). After the run, sanity check

### Prompt 2 (follow-up prompt)

> wait, i thought we are in hw5 folder

**What was lacking:** The vibe coder session had been opened in the parent course folder, so Claude Code couldn't load `HW 5/.mcp.json` and the tools couldn't be called; after the session moved into the HW 5 folder, the three `campus-customs` tools loaded and were tested live.

### Prompt 3 (sanity check)

> after you finish, sanity check — [screenshots of Problem 4 Panels A and B]

**What was lacking:** Each test in `mcp_smoke.json` showed a ticket-specific prompt the vibe coder had written itself, as if I had typed it, so it was relabeled to show my real prompt and mark the per-tool requests as the vibe coder's; the three tools were also re-run after the move to HW 5 and gave identical outputs.

---

## Problem 5 — Build the agent team and grow the MCP tools

### Prompt 1 (first prompt)

> ok P5. Lets build the agents with pydantic AI - Boss, inventory, accountung ,facilities, and customer service. include prompts, models, and agent loops and whatever necessary to make them delegate work and talk to each other without any problems. Save the agent prompts in a prompts file - backend/prompt. make sure you have one file per agent. Put the data types in backend/models.py, and the agent files under backend/. Apply the APIkey, use only gpt-6-luna for the agents. Let each agent do their job as the name suggests - boss, inventory, etc. like boss, controlling the whole situation. Inventory control the inventory, report the problems, numbers etc. accounting make sure money issues is clear, take controls of the money stuff. Facilities control monitor the facilities, and customer service handle the customers, and be nice, assume good wills. Outside of that, feel free to add tools that agents need. add them to the MCP server so they can work on the open tickets. SHop facts come from the MCP server with that campus customs new file. Don't do anything halucination/ Wire the agents so they are append to screenshot place as they run. In the harness, make sure you get each agent and the MCP tool. Add the safety section that assume this is a real business, what are the rules of thumbs? Update the readme file so the tool list matches what we have. If you need agent's figure, use the pic here — [screenshot of the Problem 5 panel about `output/audit_trail.json`, the harness agent/tool/safety list, and updating `mcp_server/README.md`; and a sheet of 16 sheltie-dog stickers to use as agent figures]

### Prompt 2 (follow-up prompt, sanity check)

> sanity check — [screenshots of Problem 5 Panels A and B]

**What was lacking:** Three agent prompts were missing some shop rules: Facilities and Customer Service did not say that a vendor with an open unpaid invoice won't ship, Facilities did not say lead times come from `vendors`, and Inventory and Customer Service did not say cash can't go negative; these were added in each agent's own terms, so all five prompts now carry every shop rule.

### Prompt 3 (additional prompt, typed during the sanity check)

> hey, you choose the stickers, thats fine

### Prompt 4 (additional prompt)

> can you showme some visible stuff? or need to wait a little bit late?

---

## Problem 6 — Plan the three tickets

### Prompt 1 (first prompt)

> ok, P6. on each open ticket, make the agent to do as what you shown me. Build output/desk_tickets.html that illustrate the tickets 101,102,103. Also add empty cash and reflection tabs for later problems, leave them blank for now.
>
> on each ticket tab, fill the expected sections only. Leave room for the actual section you will fill after you run the agents. For each expected section, wrte down:
>
> 1. who the boss should call first, why?
> 2. the agent delegation you expected, not boss randomly call everyone,
> 3. which mcp tool is expected to use.
>

### Prompt 2 (sanity check)

> sanity check — [screenshots of Problem 6 Panels A and B]

**Result:** Nothing in the plan was lacking: every ticket tab has an Expected section with who the Boss calls first and why, every expected delegation (each ticket uses two or three of the four specialists, with one agent-to-agent handoff), and the expected MCP tools, plus an empty Actual section; Cash and Reflection say "coming later". Two small fixes were made so the page also works when double-clicked: the tab script no longer errors on `file://`, and the sticker image is readable.

### Prompt 3 (additional prompt)

> show me my prompt file

### Prompt 4 (follow-up prompt: my own plan for the Expected sections)

> ok, go back to log the prompt for what i need to write down for the expected session.
>
> 1. who the boss should call first
>    1. inventory.
>    2. facility.
>    3. inventory.
> 2. All the agents -
>    1. Inventory + accounting + customer service.
>    2. Facility + accounting.
>    3. Inventory, accounting, customer serivice.
> 3. MCP tools - too much, please write for me

**What was lacking:** The Expected sections had been written from the dry run without my own plan on record, so I typed who the Boss calls first and which agents each ticket needs (101, 102, 103 in order); the vibe coder checked that `desk_tickets.html` matches it and wrote the MCP tool lists for me.

### Prompt 5 (sanity check, typed while the plan was being added)

> after the run, sanity check again, make sure i am doing ok here

**Result:** My plan (who the Boss calls first, and which agents each ticket needs) matches the Expected section on every tab, and no ticket sends all four specialists. Each ticket tab now also shows my plan in my own words at the top of its Expected section.

---

## Problem 7 — Backend routes

### Prompt 1 (first prompt)

> ok, p7. lets make the backend better. In backend/main.py, use the FastAPI and add routes so it will do the following as screenshot. From the backend/ folderm start the server with - uvicorn main:app --reload --port 8000. In output/harness.md, lst each route in one line, stating what URL, what it does — [screenshot of the six route requirements: return the three tickets and open/resolved, run the agent team on a ticket id, return recent agent events, approve a payment or purchase after a human clicks approve, return the checking balance from `cash_accounts`, reset the database]

### Prompt 2 (follow-up prompt, sanity check)

> sanity check - — [screenshots of Problem 7 Panels A and B]

**What was lacking:** Every required route existed and worked, but the route list in `harness.md` wrote three URLs as `{id}` while the code uses `{ticket_id}`, so the harness was corrected to match the code exactly; the check also confirmed that only the human approve route can change cash, that `uvicorn main:app --reload --port 8000` starts from `backend/`, and that the Vite origin is allowed.

---

## Problem 8 — Agent dashboard

### Prompt 1 (first prompt)

> ok P8, build the dashboard in frontend with React + Vite+Typescript. The frontend should call the backend route and work well. It should have the stuff shown in the screenshot. for the layout, you can check my Mika project under MBA companion. Or Yale website - https://yale.bncollege.com/. make it creative and vivid . Make sure it is easy to use and read for human. Make sure front and backend talk to each other. Back end is localhost:8000. Make sure the backend allpws the vite page origin (usually 5173) So the browswer can call those routes. Start the board with [npm run dev]. Write output/design,md with the desgn of the front end - lay out, how does agents read, etc and why. make it creative and vivid. — [screenshot of the board requirements: list three tickets, pick one and start the team, show each agent while it runs, mark resolved, per-agent summary, human approve, checking balance that drops after an approved pay; make it look good and creative]

### Prompt 2 (follow-up prompt, sanity check)

> sanity check — [screenshots of Problem 8 Panels A and B]

**What was lacking:** Every board requirement was met and tested (12 backend routes called directly at `http://localhost:8000`, CORS allows `http://localhost:5173`, `npm run dev`, nothing hard-coded), but `design.md` did not spell out when a ticket is marked resolved, so a short section now explains that a run with nothing left to sign is resolved as it finishes, while a run that prepared a payment or quote is resolved the moment a human approves it.

### Prompt 3 (additional prompt)

> show me the front end

---

## Problem 9 — Resolve the tickets

### Prompt 1 (first prompt)

> ok P9, reset the db and run all three tickets. Open the desk_tickets.html from P6, on each tab, fill in the actual section from this run. Record all the details;. On cash tab, itemize the money as the screenshot - — [screenshot of the Cash tab requirements (starting balance after reset, cash change per ticket and why, ending balance matching `cash_accounts`) and the extra files: `resolved_tickets.json`, `resolved_board.html`, appending real runs to `audit_trail.json`, finishing `harness.md`]

### Prompt 2 (sanity check)

> sanity check — [screenshots of Problem 9 Panels A and B]

**Result:** Nothing was lacking. A script checked every deliverable against the database: the reset start balance ($3,400.00); each ticket's Actual section (first call, delegations, MCP tools, Expected vs actual, board screenshot) with the Expected section kept; the Cash tab (−$840.00, −$2,400.00, $0.00, ending $160.00 = `cash_accounts`); `resolved_tickets.json` (id, final status, outcome, agent contributions, human approvals); `resolved_board.html` (three embedded screenshots); and the graded runs appended to `audit_trail.json` without removing older entries.

---

## Problem 10 — Reflection

### Prompt 1 (first prompt)

> ok P10, fill the reflection tab in desk_tickets.html. answer those qs. Make sure to tie the answer to the tickest and the app. Use the ticket tabs and cash tab on the same page as the evidence. Give more campus customs details — [screenshot of the five reflection questions: evaluate the agents on each ticket, Actual vs Expected per ticket, what would be simpler as one agent and why, three new problems the team could solve, three it could not and what tools/agents it would need]

### Prompt 2 (additional prompt)

> Use the openAI key i gave you, forget about the old key

### Prompt 3 (follow-up prompt, sanity check)

> sanity check — [screenshots of Problem 10 Panels A and B]

**What was lacking:** All five questions were answered on the Reflection tab and all 20 factual claims checked out against the database, but section 2 (Actual vs Expected) named only agents with no Campus Customs details, and sections 4–5 barely tied the new problems back to tickets 101–103, so each row and item now says what was actually passed along ($840 invoice #501, $2,400 lease due 2026-09-02, quote #1 at $52.20) and links to the ticket or Cash tab it builds on.

---

## Problem 11 — Submit to GitHub

### Prompt 1 (first prompt)

> ok P11, push everything to a public GitHub repo. Put repo URL in output/github_url.txt
>
> DO NOT PUSH THE REAL .env TO THE GITHUB. save the key on my local only. do include both database file under data so the grader can see. Have the layout as screenshot. Read me should explain as the third screenshot - — [screenshots of the expected file layout and the README requirements: copy the original DB to the working copy for a clean run, start the MCP server, start the FastAPI backend, start the React board, reset the DB before a full three-ticket run]

### Prompt 2 (sanity check, typed while the repo was being prepared)

> after finish, sanity check — [screenshots of the full Problem 11 page]

**Result:** Nothing was lacking. The repo is public (anonymous access returns 200), and a fresh clone matches the expected layout file for file, has no `.env`, and carries both databases byte-identical to my local ones (working copy = graded end state, $160.00). Following the README in the clone worked: `pip install -r requirements.txt`, `npm install` + build, the MCP server listed its 16 tools, and `uvicorn main:app --reload --port 8000` from `backend/` reported gpt-6-luna. The README covers all five required steps.

### Prompt 3 (additional prompt)

> you have my github right? if not i will give you credential

(No credentials were needed: the GitHub CLI was already logged in as garychen836 from HW 4.)
