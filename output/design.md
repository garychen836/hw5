# Campus Customs Desk — dashboard design

> *A shop counter where five little dogs run the store, and the human keeps the keys to the till.*

The board lives in `frontend/` (React + Vite + TypeScript). Start it with `npm run dev`, then open http://localhost:5173. It talks to the FastAPI backend at `http://localhost:8000`, which allows that origin.

---

## The idea: a real desk, not a log viewer

Most agent dashboards look like a terminal. Campus Customs is a **shop**: a Yale gift store on Chapel Street with order slips, a stockroom, a landlord and a cash drawer. So the board is laid out like the counter you'd stand behind:

- the **rail** where order slips get clipped
- the **shop floor** where the staff work
- the **till**
- a **tray** of things waiting for the manager's signature

Someone who has never heard of "multi-agent orchestration" can still read it at a glance: *who's working, what they're saying, and what needs me.*

The look borrows from two places I know well:

- **The Yale bookstore** ([yale.bncollege.com](https://yale.bncollege.com/)): the deep Yale-blue header, the gold promo strip across the top, clean white product cards.
- **Mika**, my MBA Companion project: navy `#0F4D92` with **Sable gold** `#E8A33D`, a serif display face for headings, soft cream cards with gentle shadows, and one colour per category.

The page background is warm "desk" paper with a faint dot grid, so the white slips and cards feel like objects sitting on a surface.

```
┌───────────── gold promo strip: shop day 2026-08-31 · gpt-6-luna · nothing sent or paid without you ─────────────┐
│  [CC] Campus Customs Desk          ┌──── TILL ────┐            Signed in at the desk as [ Gary Chen ]          │
│  Five agents run the shop…         │  $3,400.00   │            1/3 resolved            [Reset database]        │
│                                    └──────────────┘                                                            │
├──────────────┬───────────────────────────────────────────────────────────────┬─────────────────────────────────┤
│ TICKET RAIL  │  ON THE FLOOR · ticket #101                         ● LIVE    │  NEEDS YOU  (1)                 │
│ ┌──clip──┐   │  [Boss] [Inventory] [Accounting] [Facilities] [Cust. Svc]     │  ┌ #101 Vendor invoice  $840 ┐  │
│ │ #101   │   │   dog    dog          dog          dog         dog            │  │ Checking 3,400 → 2,560     │  │
│ │ slip   │   │  bubble bubble       bubble       bubble      bubble          │  │ [Approve $840]  [Reject]   │  │
│ │ ▬▬▬▬   │   │  Handoffs: Boss→Inventory · Inventory→Accounting (a→a) · …    │  └───────────────────────────┘  │
│ └────────┘   │  LIVE FROM THE FLOOR (chat feed, newest at the bottom)        │  Message drafts (never sent)    │
│ #102 · #103  │  WHAT EACH AGENT DID (Boss's call + one card per agent)       │  ✉ To Tauhid Zaman ▾            │
└──────────────┴───────────────────────────────────────────────────────────────┴─────────────────────────────────┘
```

---

## Layout, column by column

### 1. Ticket rail (left): order slips on a metal rail

Each ticket is a **paper order slip** hanging from a little metal clip on a rail:
- cream paper, a torn, perforated bottom edge, and a dashed rule under the ticket number
- a slight tilt on each slip, so the rail looks hand-hung, not printed

**What each slip shows:**
- the ticket number in big serif, the type ("Customer order", "Rent notice", "Discount request"), the subject, and who it's from
- the exact item in monospace (`1 × CC-TEE-WHITE · size S`), because that's what the stockroom reads

**Progress:** a four-step stepper under each slip: **Open → Team at work → Your call → Resolved**. It turns green as steps complete, and the current step glows gold.

**Resolved:** a green rubber **RESOLVED** stamp thumps onto the slip with a little overshoot animation, carrying the 谢谢! (thank-you) dog. A finished ticket should *feel* finished.

**When a ticket is marked resolved.** The moment a run finishes, the slip changes; what it shows depends on what the team left behind:
- **Nothing for a human to sign:** the team's last step marks the ticket resolved, and the stamp lands as the run ends.
- **The team prepared a payment, purchase or quote:** the slip moves to **Your call**, the button reads **Team done**, and a gold flag points to the tray. The RESOLVED stamp lands the moment you approve or confirm the last item, with no second run needed.

This is deliberate. The shop rule says no payment happens without a human, so a ticket whose bill is still unpaid isn't really resolved yet. The board never shows "resolved" while money is still waiting on someone.

**Running the team:** one big Yale-blue **Run the team** button per slip. While any run is going, every Run button is disabled, because all three tickets share one cash account. Once the team is done and a payment is waiting, the button reads **Team done**, and a gold flag says **"1 waiting for you →"**, pointing your eye to the tray on the right.

### 2. On the floor (centre): five dogs at five stations

The centre of the board is the **shop floor**: five stations side by side, one per agent. Each has its own sticker dog from my sticker sheet, chosen to match the job:

| Agent | Sticker | Why this one | Colour |
|---|---|---|---|
| **Boss** | 暗中观察 *(quietly watching)* | The Boss peeks over the whole floor and decides who moves | Yale blue `#00356b` |
| **Inventory** | 努力干活 *(working hard)* | Digging through the stockroom, counting sizes | Green `#0e8355` |
| **Accounting** | 搬砖中 *(grinding away)* | Glasses on, laptop out, money first | Sable gold `#b7791f` |
| **Facilities** | 嗯? *(hmm?)* | "Is that really what the lease says?" It checks the landlord's claim | Purple `#7a3fb8` |
| **Customer Service** | 收到! *(got it!)* | Holding a letter with a heart: kind, warm, assumes good will | Pink `#c2307a` |

Every station shows its name, a one-line job description, a **speech bubble**, and a status badge. The station's state is easy to read from across the room:

- **Idle:** the dog is grey and faded, and the bubble says *"Off the floor for this ticket."* Because only the right specialists light up, you can **see** that the Boss did not send everyone to every ticket.
- **Working:** the station fills with the agent's own colour, gets a coloured border and lifts slightly. The dog gently bobs, and three dots pulse in the bubble. The bubble shows what it is doing in plain words: *"checking the shelf"*, *"pulling the invoice"*, *"preparing a payment"* (each MCP tool has a human label), or its own words when the model speaks.
- **Waiting on a teammate:** a dashed border and *"Waiting on Accounting"*, so you can see a delegation chain in progress.
- **Done:** a soft tint, the agent's summary in the bubble, and a green **done · 8 steps** badge.

Under the stations sits a **handoff trail**: chips that pop in as delegations happen (**Boss → Inventory**). An **agent → agent** handoff, such as **Inventory → Accounting**, gets an orange chip with a little "AGENT → AGENT" tag. It's the clearest proof the team has full connectivity, so it gets its own colour.

### 3. Live from the floor (centre): the chatter

A chat-style feed, newest at the bottom, auto-scrolling while a run is live (a red pulsing **● LIVE** badge sits in the corner). Every line has the agent's sticker as an avatar and a coloured left edge in that agent's colour, so you can follow one voice down the page.

| Line | How it looks |
|---|---|
| A handoff | Light blue band. Orange for agent-to-agent, with the actual task quoted ("Ticket 101: please prepare the payment for invoice #501, $840…") |
| A tool call | The plain-English action plus the exact call in code font, e.g. `check_stock(sku=CC-TEE-WHITE, size=S, qty_needed=1)`, for anyone who wants to audit |
| A tool result | A small ✓ or ✕ line. Click it to expand the full JSON the MCP server returned |
| An agent finishing | Green band with its summary |
| The run ending | A quiet gold line with model calls, input tokens and **% cached**, a small tokenomics readout on every run |

When nothing is running, the feed shows the 晚安 *(good night)* dog asleep: *"Quiet on the floor."*

### 4. What each agent did (centre, after a run)

When the run ends, a summary card slides in:

- **The Boss's call:** the Boss's sticker, its outcome in plain English, and the cash impact it reported. Pills say what the status was **when the team finished** and, after you approve, **resolved now**, so the summary never shows a stale state.
- **One card per agent that actually worked**, tinted in its colour: what it did in one sentence, the ids it prepared ("payment request #1, $840, pending"), and chips of the MCP tools it used. If the Boss had to ask someone twice, the card says *"asked 2×"*.
- **The route**, written out: *Boss → Inventory · Inventory → Accounting · Boss → Customer Service*. That's exactly what Problem 9 compares against the plan.

### 5. Needs you (right): the manager's tray

The right column is the one part that belongs to the **human**. A red badge counts the items, pulsing when something is waiting.

- **Payment cards**, with a green top edge:
  - the kind (vendor invoice, rent, restock order), the amount in big serif, the payee, and the reason the agent wrote
  - a preview line: **Checking $3,400.00 → $2,560.00**. If a pay would push the balance below zero, it turns red and says *not enough cash*
  - who prepared it
  - two buttons: **Approve $840** and **Reject**
- **Quote cards**, with a gold top edge: for example 20 × navy hoodie M at $52.20 (10% off), total, margin per unit, *"no cash moves"*, and a **Confirm quote** button.
- **Review & close:** if the team finished and nothing needs paying, one button marks the ticket resolved.
- **Message drafts** (never sent): click a draft to unfold it as a cream **letter** in serif type, signed *"drafted by Customer Service, for a human to send."* Nothing on this board can send an email.

**You must type your name** at the top before any button works. The backend refuses names like "Boss" or "accounting", so a person, not an agent, signs every payment. The name is remembered in the browser.

**Toasts with feelings:** after each action, a toast pops up at the bottom with the right dog:
- 开心 *(happy)* on green when a payment goes through
- 震惊! *(shocked)* on red when something is refused, such as not enough cash, or a vendor still blocked by an open invoice
- 谢谢! when the team finishes

### 6. The till (top centre): the number everyone watches

The checking balance from `cash_accounts` sits in the header in big serif digits, because cash is the one number that matters most to a small shop. When a human approves a pay:
- the digits **count down** to the new balance
- a red **−$840.00** chip drops away beneath it

You *see* the money leave. While payments are pending, a gold pill shows how much is waiting, with *"→ $160.00 if all approved"*, so overcommitting is obvious before anyone clicks.

---

## Why these choices

- **It's a physical metaphor because the business is physical.** Slips, a rail, a stamp, a till and a tray map one-to-one onto tickets, status, cash and approvals. Nobody needs a legend.
- **Each agent gets one colour, one dog and one job.** The same colour carries through the station, the feed lines, the handoff chips and the summary cards, so you can follow Accounting across the whole page without reading a name.
- **Idle agents go grey on purpose.** The assignment warns against "Boss calls everyone". On this board you can *see* which two or three specialists lit up for each ticket.
- **The human's area is separate and loud.** Agents only *prepare*. Every decision that moves money or speaks for the shop lives in one column with big, explicit buttons, a cash preview and a required name. That is the "leave the choice to the human" principle built into the layout.
- **Plain words first, exact detail one click away.** A manager reads *"pulling the invoice"*; an auditor expands the line and sees `get_invoice_status(invoice_id=501)` and the raw JSON. The same events are appended to `output/audit_trail.json`.
- **It's honest about state.** The stepper, stamp and pills come straight from the database through the backend, never from the UI guessing. A ticket shows **Resolved** only when the database says so: after the team finishes *and* a human has approved what it prepared.
- **It's cheap to watch.** The board polls small endpoints (events since the last one seen, every second during a run; tickets and cash every 2.5 s) and shows token use and cache rate on every run, so cost stays visible.
- **It's delightful, a bit.** Bobbing dogs, a stamp that thumps, a till that counts down, letters that unfold. It's a desk people would actually enjoy sitting at, which is the brief. Motion is switched off for anyone who prefers reduced motion.

## Files

| File | What it is |
|---|---|
| `src/App.tsx` | Board state, polling, actions (run, approve, reject, confirm, resolve, reset) |
| `src/api.ts` | Calls to the FastAPI routes at `http://localhost:8000` (`VITE_API_BASE` to override) |
| `src/agents.ts` | The five agents: colours, roles, sticker crops, plain-English tool labels |
| `src/components/TicketRail.tsx` | Order slips, stepper, stamp, Run button |
| `src/components/AgentFloor.tsx` | Stations, speech bubbles, handoff trail |
| `src/components/LiveFeed.tsx` | Chat-style event feed with expandable tool results |
| `src/components/RunSummary.tsx` | Boss's call and per-agent cards |
| `src/components/NeedsYou.tsx` | Approvals, quotes, drafts |
| `src/components/CashTill.tsx` | Animated checking balance |
| `src/styles.css` | All styling (no UI framework) |
| `public/agent_stickers.jpg` | The 4 × 4 sticker sheet, cropped with CSS |
