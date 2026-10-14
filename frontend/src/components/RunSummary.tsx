import { AGENT, AGENTS, STICKERS, stickerStyle } from '../agents'
import type { AgentId, AgentReport, RunInfo } from '../types'
import { safeParse } from './AgentFloor'

/** After a run: the Boss's call, then one card per agent on what they did. */
export function RunSummary({ run, ticketResolved }: { run: RunInfo | null; ticketResolved: boolean }) {
  if (!run) return null
  const res = run.resolution
  const reports: Record<string, AgentReport[]> = {}
  for (const [id, a] of Object.entries(run.agents ?? {})) {
    reports[id] = a.outputs.map(o => (typeof o === 'string' ? safeParse(o) : o) as AgentReport)
  }
  const did = Object.fromEntries((res?.contributions ?? []).map(c => [c.agent, c.did]))
  const worked = AGENTS.filter(a => a.id in (run.agents ?? {}) || did[a.id])
  const u = run.usage_total
  return (
    <section className="summary" aria-label="What each agent did">
      <div className="summary-head">
        <h2 className="col-title">What each agent did · ticket #{run.ticket_id}</h2>
        {u && <span className="tokens">{u.requests} calls · {u.input_tokens.toLocaleString()} in ({Math.round(100 * u.cached_tokens / Math.max(u.input_tokens, 1))}% cached) · {u.output_tokens.toLocaleString()} out</span>}
      </div>
      {res && (
        <div className="verdict">
          <div className="dog dog-sm" style={stickerStyle(STICKERS.boss)} aria-hidden />
          <div>
            <div className="verdict-title">The Boss’s call <span className="pill">{res.final_status.replaceAll('_', ' ')} when the team finished</span>{ticketResolved && <span className="pill pill-ok">resolved now</span>}</div>
            <p>{res.outcome}</p>
            <p className="muted">{res.cash_impact}</p>
          </div>
        </div>
      )}
      <div className="cards">
        {worked.filter(a => a.id !== 'boss').map(a => {
          const rs = reports[a.id] ?? []
          const last = rs[rs.length - 1]
          return (
            <article key={a.id} className="card" style={{ ['--c' as string]: a.color, ['--cs' as string]: a.soft }}>
              <div className="card-top"><div className="dog dog-xs" style={stickerStyle(STICKERS[a.id as AgentId])} aria-hidden /><b>{a.title}</b>
                {rs.length > 1 && <span className="muted">asked {rs.length}×</span>}</div>
              <p>{did[a.id] ?? last?.summary}</p>
              {last?.actions && last.actions.length > 0 && <ul>{last.actions.slice(0, 3).map((x, i) => <li key={i}>{x}</li>)}</ul>}
              <div className="tools">{[...new Set(run.agents[a.id]?.tools_used ?? [])].filter(t => t !== 'final_result').map(t => <code key={t}>{t}</code>)}</div>
            </article>
          )
        })}
      </div>
      {run.handoffs && run.handoffs.length > 0 && (
        <div className="route">Route: {run.handoffs.map(h => `${AGENT[h.from as AgentId]?.title ?? h.from} → ${AGENT[h.to as AgentId]?.title ?? h.to}`).join('  ·  ')}</div>
      )}
    </section>
  )
}
