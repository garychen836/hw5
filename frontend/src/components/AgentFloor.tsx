import { AGENT, AGENTS, STICKERS, TOOL_LABEL, stickerStyle } from '../agents'
import type { AgentId, BoardEvent } from '../types'

export type AgentState = 'idle' | 'working' | 'waiting' | 'done'

/** What each agent is doing right now, worked out from the run's events. */
export function agentStates(events: BoardEvent[]) {
  const state: Record<string, { state: AgentState; line: string; steps: number }> = {}
  for (const a of AGENTS) state[a.id] = { state: 'idle', line: 'Off the floor for this ticket', steps: 0 }
  for (const e of events) {
    const s = state[e.agent]
    if (!s) continue
    if (e.event === 'agent_start') { s.state = 'working'; s.line = 'Picked up the task' }
    if (e.event === 'model_step') {
      s.steps += 1
      const tools = (e.tools ?? []).filter(t => t !== 'final_result')
      if (e.said && e.said !== 'null') s.line = e.said
      else if (tools.length) s.line = tools.map(t => TOOL_LABEL[t] ?? t).join(' · ')
      else s.line = 'Writing the report'
      s.state = 'working'
    }
    if (e.event === 'handoff' && e.to) { s.state = 'waiting'; s.line = `Waiting on ${AGENT[e.to as AgentId]?.title ?? e.to}` }
    if (e.event === 'tool_result' && e.tool === 'ask_teammate') { s.state = 'working'; s.line = 'Got the report back' }
    if (e.event === 'agent_done') {
      s.state = 'done'
      const out = typeof e.output === 'string' ? safeParse(e.output) : e.output
      s.line = (out as { summary?: string; outcome?: string })?.summary ?? (out as { outcome?: string })?.outcome ?? 'Done'
    }
    if (e.event === 'agent_error' || e.event === 'limit_hit') { s.state = 'done'; s.line = e.error ?? 'Stopped' }
  }
  return state
}

export function safeParse(s: string): unknown {
  try { return JSON.parse(s) } catch { return s }
}

/** The shop floor: five stations, one sticker dog each, lit up while they work. */
export function AgentFloor({ events, running }: { events: BoardEvent[]; running: boolean }) {
  const states = agentStates(events)
  const handoffs = events.filter(e => e.event === 'handoff')
  return (
    <section className="floor" aria-label="Agents">
      <div className="stations">
        {AGENTS.map(a => {
          const s = states[a.id]
          return (
            <div key={a.id} className={`station st-${s.state}`} style={{ ['--c' as string]: a.color, ['--cs' as string]: a.soft }}>
              <div className="dog" style={stickerStyle(STICKERS[a.id])} role="img" aria-label={`${a.title} sticker`} />
              <div className="station-name">{a.title}</div>
              <div className="station-role">{a.role}</div>
              <div className="bubble" aria-live="polite" title={s.line}>
                {s.state === 'working' && <span className="dots" aria-hidden><i /><i /><i /></span>}
                <span>{s.line}</span>
              </div>
              <div className="station-badge">
                {s.state === 'idle' ? 'idle' : s.state === 'done' ? `done · ${s.steps} steps` : s.state === 'waiting' ? 'waiting on a teammate' : `step ${s.steps}`}
              </div>
            </div>
          )
        })}
      </div>
      <div className="handoffs" aria-label="Handoffs">
        <span className="handoffs-label">Handoffs</span>
        {handoffs.length === 0 && <span className="muted">{running ? 'The Boss is reading the ticket…' : 'None yet — pick a ticket and run the team'}</span>}
        {handoffs.map(h => {
          const from = AGENT[h.agent as AgentId], to = AGENT[h.to as AgentId]
          const a2a = h.agent !== 'boss'
          return (
            <span key={h.seq} className={`handoff ${a2a ? 'a2a' : ''}`} title={h.task}>
              <b style={{ color: from?.color }}>{from?.title ?? h.agent}</b> → <b style={{ color: to?.color }}>{to?.title ?? h.to}</b>
              {a2a && <em>agent → agent</em>}
            </span>
          )
        })}
      </div>
    </section>
  )
}
