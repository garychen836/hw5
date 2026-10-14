import type { BoardEvent, Cash, RunInfo, Ticket } from './types'

export const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, {
    ...init,
    headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `${res.status} ${res.statusText}`)
  return body as T
}

const post = <T,>(path: string, data?: unknown) =>
  call<T>(path, { method: 'POST', body: data === undefined ? undefined : JSON.stringify(data) })

export const api = {
  health: () => call<{ ok: boolean; model: string; key_source: string; active_run: string | null }>('/api/health'),
  tickets: () => call<{ today: string; tickets: Ticket[] }>('/api/tickets'),
  cash: () => call<Cash>('/api/cash'),
  events: (since: number, runId?: string) =>
    call<{ events: BoardEvent[]; last_seq: number; active_run: string | null }>(
      `/api/events?since=${since}&limit=500${runId ? `&run_id=${encodeURIComponent(runId)}` : ''}`),
  runs: () => call<{ runs: { run_id: string; ticket_id: number; started: string; status: string }[] }>('/api/runs'),
  run: (runId: string) => call<RunInfo>(`/api/runs/${encodeURIComponent(runId)}`),
  start: (ticketId: number) => post<{ run_id: string }>(`/api/tickets/${ticketId}/run`),
  approve: (id: number, name: string) => post<{ balance_before: number; balance_after: number; source_update: string; ticket_status: string | null }>(`/api/payments/${id}/approve`, { name }),
  reject: (id: number, name: string) => post<unknown>(`/api/payments/${id}/reject`, { name }),
  confirmQuote: (id: number, name: string) => post<{ ticket_status: string | null }>(`/api/quotes/${id}/confirm`, { name }),
  resolve: (ticketId: number, name: string) => post<unknown>(`/api/tickets/${ticketId}/resolve`, { name }),
  reset: () => post<{ message: string }>('/api/reset'),
}
