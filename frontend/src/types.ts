export type AgentId = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface PaymentRequest {
  id: number; ticket_id: number; kind: 'invoice' | 'rent' | 'purchase_order'; ref_id: number | null
  payee: string; amount: number; reason: string; status: 'pending' | 'approved' | 'rejected'
  requested_by: string; sku?: string | null; size?: string | null; qty?: number | null
  expected_arrival?: string | null; decided_by?: string | null
}

export interface Quote {
  id: number; ticket_id: number; sku: string; size: string; qty: number; list_price: number
  quoted_unit_price: number; discount_pct: number; margin_per_unit: number; total_price: number
  total_margin: number; status: 'draft' | 'confirmed'; prepared_by: string
}

export interface MessageDraft {
  id: number; ticket_id: number; recipient: string; subject: string; body: string; written_by: string
}

export interface Ticket {
  id: number; type: string; requester: string; subject: string; sku: string | null; size: string | null
  qty: number | null; lease_id: number | null; invoice_id: number | null; notes: string; created_at: string
  status: 'open' | 'in_progress' | 'waiting_on_human' | 'resolved'
  resolved: boolean; running: boolean
  pending_payments: PaymentRequest[]; draft_quotes: Quote[]; message_drafts: MessageDraft[]
}

export interface Cash {
  balance: number; balance_date: string; pending_requests_total: number
  balance_if_all_pending_approved: number; payments_made_count: number; payments_made_total: number
}

export interface BoardEvent {
  seq: number; ts: string; run_id: string; ticket_id: number | null; agent: string; agent_title: string
  chain: string; event: string
  said?: string | null; tools?: string[]; tool_args?: { tool: string; args: Record<string, unknown> }[]
  tokens?: { input: number; cached: number; output: number }
  tool?: string; result?: string; to?: string; task?: string; reason?: string; output?: unknown
  error?: string; status?: string; usage_total?: Usage; handoffs?: Handoff[]
  action?: string; by?: string
}

export interface Usage { requests: number; input_tokens: number; cached_tokens: number; output_tokens: number }
export interface Handoff { no: number; from: string; to: string; task: string }

export interface AgentReport {
  summary: string; facts?: string[]; actions?: string[]; needs_human?: string[]; open_questions?: string[]
}
export interface Resolution {
  ticket_id: number; final_status: string; outcome: string
  contributions: { agent: AgentId; did: string }[]; human_approvals_needed: string[]; cash_impact: string
}

export interface RunInfo {
  run_id: string; status: string; ticket_id: number
  resolution: Resolution | null
  agents: Record<string, { title: string; outputs: unknown[]; tools_used: string[] }>
  handoffs: Handoff[] | null; usage_total: Usage | null
}
