import { STICKERS, stickerStyle } from '../agents'
import type { Ticket } from '../types'

const TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Discount request',
}

const STEPS = ['Open', 'Team at work', 'Your call', 'Resolved'] as const

function stepOf(t: Ticket): number {
  if (t.status === 'resolved') return 3
  if (t.running || t.status === 'in_progress') return 1
  if (t.status === 'waiting_on_human') return 2
  return 0
}

function detail(t: Ticket): string {
  if (t.sku) return `${t.qty} × ${t.sku} · size ${t.size}`
  if (t.lease_id) return `Lease #${t.lease_id}`
  return t.notes
}

interface Props {
  tickets: Ticket[]
  selected: number | null
  busy: boolean
  onSelect: (id: number) => void
  onRun: (id: number) => void
}

/** Order slips clipped to the desk rail, one per ticket. */
export function TicketRail({ tickets, selected, busy, onSelect, onRun }: Props) {
  return (
    <aside className="rail" aria-label="Tickets">
      <h2 className="col-title">Ticket rail</h2>
      {tickets.map(t => {
        const step = stepOf(t)
        const waiting = t.pending_payments.length + t.draft_quotes.length
        return (
          <article
            key={t.id}
            className={`slip ${selected === t.id ? 'slip-on' : ''} ${t.resolved ? 'slip-done' : ''}`}
            onClick={() => onSelect(t.id)}
            tabIndex={0}
            onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && onSelect(t.id)}
            aria-pressed={selected === t.id}
          >
            <div className="slip-clip" aria-hidden />
            <div className="slip-head">
              <span className="slip-no">#{t.id}</span>
              <span className="slip-type">{TYPE_LABEL[t.type] ?? t.type}</span>
            </div>
            <div className="slip-subject">{t.subject}</div>
            <div className="slip-from">from <b>{t.requester}</b></div>
            <div className="slip-detail">{detail(t)}</div>

            <ol className="stepper" aria-label={`Status: ${STEPS[step]}`}>
              {STEPS.map((s, i) => (
                <li key={s} className={i < step ? 'done' : i === step ? 'now' : ''}>{s}</li>
              ))}
            </ol>

            {t.resolved && (
              <div className="stamp" aria-label="Resolved">
                <span className="stamp-dog" style={stickerStyle(STICKERS.thanks)} aria-hidden />RESOLVED
              </div>
            )}
            {!t.resolved && waiting > 0 && !t.running && (
              <div className="slip-flag">{waiting} waiting for you →</div>
            )}

            {!t.resolved && (
              <button
                className="btn btn-run"
                disabled={busy || t.status === 'waiting_on_human'}
                onClick={e => { e.stopPropagation(); onRun(t.id) }}
                title={t.status === 'waiting_on_human' ? 'The team is done; your approval is next' : 'Start the agent team'}
              >
                {t.running ? 'Team at work…' : t.status === 'waiting_on_human' ? 'Team done' : step === 0 ? 'Run the team' : 'Run again'}
              </button>
            )}
          </article>
        )
      })}
    </aside>
  )
}
