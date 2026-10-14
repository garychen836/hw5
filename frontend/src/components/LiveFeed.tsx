import { useEffect, useRef, useState, type ReactNode } from 'react'
import { AGENT, STICKERS, TOOL_LABEL, stickerStyle } from '../agents'
import type { AgentId, BoardEvent } from '../types'
import { safeParse } from './AgentFloor'

function short(v: unknown, n = 140): string {
  const s = typeof v === 'string' ? v : JSON.stringify(v)
  return s.length > n ? s.slice(0, n) + '…' : s
}

function argText(args: Record<string, unknown>): string {
  return Object.entries(args)
    .filter(([k]) => !['requested_by', 'prepared_by', 'written_by', 'updated_by', 'reason', 'body', 'note'].includes(k))
    .map(([k, v]) => `${k}=${short(v, 40)}`).join(', ')
}

/** One line in the feed. Returns null for events the board doesn't need to show. */
function Line({ e }: { e: BoardEvent }) {
  const [open, setOpen] = useState(false)
  const a = AGENT[e.agent as AgentId]
  const who = <b style={{ color: a?.color ?? 'var(--ink)' }}>{a?.title ?? e.agent_title}</b>
  let body: ReactNode = null
  let cls = ''
  switch (e.event) {
    case 'run_start': body = <>Run started · model <code>gpt-6-luna</code></>; cls = 'sys'; break
    case 'agent_start':
      if (e.agent === 'boss') return null
      body = <>{who} picked up: <q>{short(e.task, 220)}</q></>; break
    case 'handoff':
      body = <>{who} asked <b style={{ color: AGENT[e.to as AgentId]?.color }}>{AGENT[e.to as AgentId]?.title ?? e.to}</b>: <q>{short(e.task, 220)}</q></>
      cls = e.agent === 'boss' ? 'handoff-line' : 'handoff-line a2a'; break
    case 'delegation_refused': body = <>{who} could not delegate: {e.reason}</>; cls = 'warn'; break
    case 'model_step': {
      const calls = (e.tool_args ?? []).filter(c => c.tool !== 'final_result')
      const said = e.said && e.said !== 'null' ? e.said : null
      if (!calls.length && !said) return null
      body = <>
        {said && <div className="said">{who}: “{said}”</div>}
        {calls.map((c, i) => (
          <div key={i}>{!said && i === 0 ? who : <span className="indent" />} {TOOL_LABEL[c.tool] ?? c.tool}
            {c.tool !== 'ask_teammate' && <code className="tool">{c.tool}({argText(c.args)})</code>}
          </div>
        ))}
      </>
      break
    }
    case 'tool_result': {
      if (e.tool === 'ask_teammate' || e.tool === 'final_result') return null
      const r = safeParse(e.result ?? '') as Record<string, unknown>
      const bad = r && (r.ok === false || r.found === false)
      body = <button className="result" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className={bad ? 'neg' : 'ok'}>{bad ? '✕' : '✓'}</span> <code>{e.tool}</code>
        {typeof r === 'object' && r && 'message' in r ? <> — {short(r.message, 110)}</> : <span className="muted"> result {open ? '▴' : '▾'}</span>}
        {open && <pre>{JSON.stringify(r, null, 2)}</pre>}
      </button>
      cls = 'res'
      break
    }
    case 'agent_done': {
      const out = (typeof e.output === 'string' ? safeParse(e.output) : e.output) as { summary?: string; outcome?: string }
      body = <>{who} finished: {out?.summary ?? out?.outcome}</>; cls = 'done'; break
    }
    case 'agent_error': case 'limit_hit': body = <>{who} stopped: {e.error}</>; cls = 'warn'; break
    case 'run_end':
      body = <>Run finished{e.usage_total ? ` · ${e.usage_total.requests} model calls · ${e.usage_total.input_tokens.toLocaleString()} input tokens (${Math.round(100 * e.usage_total.cached_tokens / Math.max(e.usage_total.input_tokens, 1))}% cached)` : ''}</>
      cls = 'sys'; break
    default: return null
  }
  return (
    <li className={`feed-line ${cls}`} style={{ ['--c' as string]: a?.color ?? '#5b6475' }}>
      <span className="feed-dot" style={a ? stickerStyle(STICKERS[a.id]) : undefined} aria-hidden />
      <div className="feed-body">{body}</div>
      <time>{e.ts.slice(11, 19)}</time>
    </li>
  )
}

/** Live chatter from the floor, newest at the bottom (auto-scrolls while running). */
export function LiveFeed({ events, running }: { events: BoardEvent[]; running: boolean }) {
  const end = useRef<HTMLLIElement>(null)
  useEffect(() => { if (running) end.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }, [events.length, running])
  return (
    <section className="feed" aria-label="Live agent feed">
      <h2 className="col-title">Live from the floor</h2>
      {events.length === 0 ? (
        <div className="empty"><div className="dog dog-sm" style={stickerStyle(STICKERS.sleepy)} /><span>Quiet on the floor. Pick a ticket on the rail and press <b>Run the team</b>.</span></div>
      ) : (
        <ol className="feed-list">{events.map(e => <Line key={e.seq} e={e} />)}<li ref={end} aria-hidden /></ol>
      )}
    </section>
  )
}
