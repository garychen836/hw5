import { useEffect, useRef, useState } from 'react'
import { money } from '../agents'
import type { Cash } from '../types'

/** The shop's till: checking balance that counts down when a human approves a pay. */
export function CashTill({ cash }: { cash: Cash | null }) {
  const [shown, setShown] = useState<number | null>(null)
  const [drop, setDrop] = useState<number | null>(null)
  const prev = useRef<number | null>(null)

  useEffect(() => {
    if (!cash) return
    const from = prev.current ?? cash.balance
    const to = cash.balance
    prev.current = to
    if (from === to) { setShown(to); return }
    if (to < from) { setDrop(from - to); setTimeout(() => setDrop(null), 2600) }
    const start = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const k = Math.min((now - start) / 900, 1)
      setShown(from + (to - from) * (1 - Math.pow(1 - k, 3)))
      if (k < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [cash])

  const pending = cash?.pending_requests_total ?? 0
  const after = cash?.balance_if_all_pending_approved ?? 0
  return (
    <section className="till" aria-label="Checking balance">
      <div className="till-label">Checking · cash_accounts</div>
      <div className="till-amount" aria-live="polite">
        {money(shown ?? cash?.balance)}
        {drop != null && <span className="till-drop">−{money(drop)}</span>}
      </div>
      <div className="till-meta">
        {pending > 0 ? (
          <>
            <span className="pill pill-gold">{money(pending)} waiting for approval</span>
            <span className={after < 0 ? 'neg' : ''}>→ {money(after)} if all approved</span>
          </>
        ) : (
          <span>No payments waiting · {cash?.payments_made_count ?? 0} paid so far ({money(cash?.payments_made_total)})</span>
        )}
      </div>
    </section>
  )
}
