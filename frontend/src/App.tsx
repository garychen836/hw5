import { useCallback, useEffect, useRef, useState } from 'react'
import { API_BASE, api } from './api'
import { STICKERS, money, stickerStyle } from './agents'
import { AgentFloor } from './components/AgentFloor'
import { CashTill } from './components/CashTill'
import { LiveFeed } from './components/LiveFeed'
import { NeedsYou } from './components/NeedsYou'
import { RunSummary } from './components/RunSummary'
import { TicketRail } from './components/TicketRail'
import type { BoardEvent, Cash, RunInfo, Ticket } from './types'

type Toast = { text: string; mood: 'happy' | 'shocked' | 'thanks' }

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [today, setToday] = useState('')
  const [cash, setCash] = useState<Cash | null>(null)
  const [selected, setSelected] = useState<number | null>(null)
  const [runByTicket, setRunByTicket] = useState<Record<number, string>>({})
  const [runId, setRunId] = useState<string | null>(null)
  const [events, setEvents] = useState<BoardEvent[]>([])
  const [runInfo, setRunInfo] = useState<RunInfo | null>(null)
  const [activeRun, setActiveRun] = useState<string | null>(null)
  const [online, setOnline] = useState(true)
  const [name, setName] = useState(() => localStorage.getItem('desk-name') ?? '')
  const [toast, setToast] = useState<Toast | null>(null)
  const [working, setWorking] = useState<string | null>(null)
  const lastSeq = useRef(0)

  const say = (text: string, mood: Toast['mood']) => {
    setToast({ text, mood })
    setTimeout(() => setToast(t => (t?.text === text ? null : t)), 4200)
  }

  // ---- board state (tickets, cash, active run) -----------------------------
  const refresh = useCallback(async () => {
    try {
      const [t, c, h] = await Promise.all([api.tickets(), api.cash(), api.health()])
      setTickets(t.tickets); setToday(t.today); setCash(c); setActiveRun(h.active_run); setOnline(true)
    } catch { setOnline(false) }
  }, [])

  const loadRuns = useCallback(async () => {
    try {
      const { runs } = await api.runs()
      const latest: Record<number, string> = {}
      for (const r of runs) if (r.ticket_id) latest[r.ticket_id] = r.run_id  // runs come oldest first
      setRunByTicket(latest)
      return latest
    } catch { return {} }
  }, [])


  useEffect(() => { localStorage.setItem('desk-name', name) }, [name])

  // ---- the run shown on the floor ------------------------------------------
  const loadRun = useCallback(async (rid: string | null) => {
    setRunId(rid); setEvents([]); setRunInfo(null); lastSeq.current = 0
    if (!rid) return
    try {
      const ev = await api.events(0, rid)
      setEvents(ev.events); lastSeq.current = ev.last_seq
      if (ev.events.some(e => e.event === 'run_end')) setRunInfo(await api.run(rid))
    } catch { /* backend offline; banner shows it */ }
  }, [])

  useEffect(() => {
    refresh()
    // ?ticket=101 opens the board on that ticket's latest run (handy for sharing and screenshots)
    loadRuns().then(latest => {
      const wanted = Number(new URLSearchParams(location.search).get('ticket'))
      if (wanted) { setSelected(wanted); loadRun(latest[wanted] ?? null) }
    })
    const id = setInterval(refresh, 2500)
    return () => clearInterval(id)
  }, [refresh, loadRuns, loadRun])

  const select = (id: number) => {
    setSelected(id)
    if (runByTicket[id] !== runId) loadRun(runByTicket[id] ?? null)
  }

  // live polling while this run is going
  useEffect(() => {
    if (!runId || runInfo) return
    let stop = false
    const tick = async () => {
      try {
        const ev = await api.events(lastSeq.current, runId)
        if (stop) return
        if (ev.events.length) {
          lastSeq.current = ev.last_seq
          setEvents(prev => [...prev, ...ev.events.filter(e => !prev.some(p => p.seq === e.seq))])
          if (ev.events.some(e => e.event === 'run_end')) {
            setRunInfo(await api.run(runId)); refresh()
            say('The team is done. Check what needs you on the right.', 'thanks')
          }
        }
      } catch { /* retry next tick */ }
    }
    const id = setInterval(tick, 1000)
    return () => { stop = true; clearInterval(id) }
  }, [runId, runInfo, refresh])

  // ---- actions --------------------------------------------------------------
  const run = async (ticketId: number) => {
    try {
      const { run_id } = await api.start(ticketId)
      setSelected(ticketId)
      setRunByTicket(m => ({ ...m, [ticketId]: run_id }))
      await loadRun(run_id)
      refresh()
    } catch (e) { say((e as Error).message, 'shocked') }
  }

  const human = async (key: string, fn: () => Promise<unknown>, ok: (r: never) => string) => {
    setWorking(key)
    try {
      const r = await fn()
      say(ok(r as never), 'happy')
    } catch (e) { say((e as Error).message, 'shocked') }
    finally { setWorking(null); refresh() }
  }

  const reset = async () => {
    if (!confirm('Reset the working database to the original values? Prepared requests, drafts and payments are cleared; the audit trail is kept.')) return
    try {
      await api.reset()
      setRunByTicket({}); loadRun(null); setSelected(null)
      say('Fresh start: database reset to the original.', 'thanks'); refresh()
    } catch (e) { say((e as Error).message, 'shocked') }
  }

  const selectedTicket = tickets.find(t => t.id === selected) ?? null
  const runningHere = !!runId && activeRun === runId
  const resolvedCount = tickets.filter(t => t.resolved).length

  return (
    <div className="app">
      <div className="promo">Campus Customs · 1 Chapel Street, New Haven · shop day <b>{today || '…'}</b> · agents run on <code>gpt-6-luna</code> · nothing is ever sent or paid without you</div>
      <header className="top">
        <div className="brand">
          <div className="crest" aria-hidden>CC</div>
          <div><h1>Campus Customs <span>Desk</span></h1><p>Five agents run the shop. You sign off on the money.</p></div>
        </div>
        <CashTill cash={cash} />
        <div className="desk-user">
          <label htmlFor="who">Signed in at the desk as</label>
          <input id="who" value={name} onChange={e => setName(e.target.value)} placeholder="Your name (for approvals)" />
          <div className="top-actions">
            <span className="progress">{resolvedCount}/3 resolved</span>
            <button className="btn btn-ghost small" onClick={reset} disabled={!!activeRun}>Reset database</button>
          </div>
        </div>
      </header>

      {!online && <div className="offline">Can’t reach the backend at {API_BASE}. Start it from <code>backend/</code> with <code>uvicorn main:app --reload --port 8000</code>.</div>}

      <main className="grid">
        <TicketRail tickets={tickets} selected={selected} busy={!!activeRun} onSelect={select} onRun={run} />

        <div className="center">
          <div className="floor-head">
            <h2 className="col-title">{selectedTicket ? <>On the floor · ticket #{selectedTicket.id} <span className="muted">— {selectedTicket.subject}</span></> : 'On the floor'}</h2>
            {runningHere && <span className="live"><i />live</span>}
          </div>
          <AgentFloor events={events} running={runningHere} />
          <LiveFeed events={events} running={runningHere} />
          <RunSummary run={runInfo} ticketResolved={!!tickets.find(t => t.id === runInfo?.ticket_id)?.resolved} />
        </div>

        <NeedsYou
          tickets={tickets} cash={cash} name={name} working={working}
          onApprove={id => human(`pay-${id}`, () => api.approve(id, name),
            (r: { balance_before: number; balance_after: number; source_update: string; ticket_status: string | null }) =>
              `Paid. Checking ${money(r.balance_before)} → ${money(r.balance_after)} · ${r.source_update}${r.ticket_status === 'resolved' ? ' · ticket resolved' : ''}`)}
          onReject={id => human(`rej-${id}`, () => api.reject(id, name), () => 'Request rejected. No money moved.')}
          onConfirmQuote={id => human(`q-${id}`, () => api.confirmQuote(id, name),
            (r: { ticket_status: string | null }) => `Quote confirmed${r.ticket_status === 'resolved' ? ' · ticket resolved' : ''}. No money moved.`)}
          onResolve={tid => human(`res-${tid}`, () => api.resolve(tid, name), () => `Ticket #${tid} marked resolved.`)}
        />
      </main>

      {toast && (
        <div className={`toast t-${toast.mood}`} role="status">
          <div className="dog dog-xs" style={stickerStyle(STICKERS[toast.mood])} aria-hidden />{toast.text}
        </div>
      )}
      <footer>Every number comes from <code>data/campus_customs_new.db</code> through the Campus Customs MCP server · every step is appended to <code>output/audit_trail.json</code></footer>
    </div>
  )
}
