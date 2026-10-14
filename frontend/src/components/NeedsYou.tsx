import { useState } from 'react'
import { AGENT, money } from '../agents'
import type { AgentId, Cash, Ticket } from '../types'

interface Props {
  tickets: Ticket[]
  cash: Cash | null
  name: string
  onApprove: (id: number) => void
  onReject: (id: number) => void
  onConfirmQuote: (id: number) => void
  onResolve: (ticketId: number) => void
  working: string | null
}

const KIND: Record<string, string> = { invoice: 'Vendor invoice', rent: 'Rent', purchase_order: 'Restock order' }

/** The human's tray: every decision the agents can't make. */
export function NeedsYou({ tickets, cash, name, onApprove, onReject, onConfirmQuote, onResolve, working }: Props) {
  const [openDraft, setOpenDraft] = useState<number | null>(null)
  const pays = tickets.flatMap(t => t.pending_payments)
  const quotes = tickets.flatMap(t => t.draft_quotes)
  const drafts = tickets.flatMap(t => t.message_drafts.map(d => ({ ...d, resolved: t.resolved })))
  const stuck = tickets.filter(t => t.status === 'waiting_on_human' && !t.pending_payments.length && !t.draft_quotes.length)
  const noName = !name.trim()
  const count = pays.length + quotes.length + stuck.length

  return (
    <aside className="tray" aria-label="Needs your decision">
      <h2 className="col-title">Needs you <span className={`count ${count ? 'hot' : ''}`}>{count}</span></h2>
      {noName && count > 0 && <div className="hint">Type your name at the top to sign approvals.</div>}
      {count === 0 && <div className="empty small">Nothing to approve. Agents only <i>prepare</i> payments — the money moves when a person approves here.</div>}

      {pays.map(p => {
        const after = (cash?.balance ?? 0) - p.amount
        return (
          <div key={p.id} className="decision pay">
            <div className="decision-top"><span className="tag">#{p.ticket_id}</span><span>{KIND[p.kind]}</span><span className="amt">{money(p.amount)}</span></div>
            <div className="payee">to <b>{p.payee}</b>{p.qty ? ` · ${p.qty} × ${p.sku} ${p.size}` : ''}</div>
            <p className="reason">{p.reason}</p>
            <div className={`impact ${after < 0 ? 'neg' : ''}`}>Checking {money(cash?.balance)} → <b>{money(after)}</b>{after < 0 && ' · not enough cash'}</div>
            <div className="by">prepared by {AGENT[p.requested_by as AgentId]?.title ?? p.requested_by}</div>
            <div className="row">
              <button className="btn btn-approve" disabled={noName || working != null} onClick={() => onApprove(p.id)}>
                {working === `pay-${p.id}` ? 'Paying…' : `Approve ${money(p.amount)}`}
              </button>
              <button className="btn btn-ghost" disabled={noName || working != null} onClick={() => onReject(p.id)}>Reject</button>
            </div>
          </div>
        )
      })}

      {quotes.map(q => (
        <div key={q.id} className="decision quote">
          <div className="decision-top"><span className="tag">#{q.ticket_id}</span><span>Price quote</span><span className="amt">{q.discount_pct}% off</span></div>
          <div className="payee">{q.qty} × {q.sku} {q.size} at <b>{money(q.quoted_unit_price)}</b> each (list {money(q.list_price)})</div>
          <div className="impact">Total {money(q.total_price)} · margin {money(q.margin_per_unit)}/unit · no cash moves</div>
          <div className="row">
            <button className="btn btn-approve" disabled={noName || working != null} onClick={() => onConfirmQuote(q.id)}>Confirm quote</button>
          </div>
        </div>
      ))}

      {stuck.map(t => (
        <div key={t.id} className="decision">
          <div className="decision-top"><span className="tag">#{t.id}</span><span>Review & close</span></div>
          <p className="reason">The team finished and nothing needs paying. Read the drafts, then close the ticket.</p>
          <button className="btn btn-approve" disabled={noName || working != null} onClick={() => onResolve(t.id)}>Mark resolved</button>
        </div>
      ))}

      {drafts.length > 0 && <h3 className="sub-title">Message drafts <span className="muted">(never sent)</span></h3>}
      {drafts.map(d => (
        <div key={d.id} className={`draft ${d.resolved ? 'faded' : ''}`}>
          <button className="draft-head" onClick={() => setOpenDraft(openDraft === d.id ? null : d.id)} aria-expanded={openDraft === d.id}>
            <span className="tag">#{d.ticket_id}</span> ✉ To <b>{d.recipient}</b> — {d.subject} <span className="muted">{openDraft === d.id ? '▴' : '▾'}</span>
          </button>
          {openDraft === d.id && <div className="letter">{d.body}<div className="sig">— drafted by Customer Service, for a human to send</div></div>}
        </div>
      ))}
    </aside>
  )
}
