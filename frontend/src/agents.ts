import type { CSSProperties } from 'react'
import type { AgentId } from './types'

// Sticker sheet is a 4 x 4 grid (public/agent_stickers.jpg). [column, row], 0-based.
type Cell = [number, number]
export const STICKERS = {
  boss: [2, 2] as Cell,              // 暗中观察 — quietly watching over the floor
  inventory: [3, 1] as Cell,         // 努力干活 — digging through the stockroom
  accounting: [2, 3] as Cell,        // 搬砖中 — glasses on, laptop out
  facilities: [1, 0] as Cell,        // 嗯? — "is that what the lease says?"
  customer_service: [0, 3] as Cell,  // 收到! — a letter with a heart
  happy: [0, 0] as Cell,             // 开心 — a payment went through
  shocked: [2, 0] as Cell,           // 震惊! — refused / not enough cash
  thanks: [1, 1] as Cell,            // 谢谢! — ticket resolved
  sleepy: [3, 3] as Cell,            // 晚安 — nothing running
}

export function stickerStyle(cell: Cell): CSSProperties {
  return {
    backgroundImage: 'url(/agent_stickers.jpg)',
    backgroundSize: '400% 400%',
    backgroundPosition: `${(cell[0] / 3) * 100}% ${(cell[1] / 3) * 100}%`,
  }
}

export interface AgentMeta { id: AgentId; title: string; role: string; color: string; soft: string }

export const AGENTS: AgentMeta[] = [
  { id: 'boss', title: 'Boss', role: 'Reads the ticket, picks the team, makes the call', color: '#00356b', soft: '#e3ebf6' },
  { id: 'inventory', title: 'Inventory', role: 'Stock by SKU & size, shortfalls, restock', color: '#0e8355', soft: '#dff6ea' },
  { id: 'accounting', title: 'Accounting', role: 'Cash, invoices, margins; prepares payments', color: '#b7791f', soft: '#fff3dc' },
  { id: 'facilities', title: 'Facilities', role: 'The shop space: lease, rent, landlord', color: '#7a3fb8', soft: '#f1e8fb' },
  { id: 'customer_service', title: 'Customer Service', role: 'Kind, honest drafts for customers', color: '#c2307a', soft: '#fce7f1' },
]
export const AGENT = Object.fromEntries(AGENTS.map(a => [a.id, a])) as Record<AgentId, AgentMeta>

export const TOOL_LABEL: Record<string, string> = {
  get_ticket: 'reading the ticket',
  list_tickets: 'scanning the board',
  check_stock: 'checking the shelf',
  find_vendors: 'looking up vendors',
  get_invoice_status: 'pulling the invoice',
  get_lease_status: 'reading the lease',
  get_cash_balance: 'checking the till',
  list_payment_requests: 'reviewing requests',
  prepare_payment: 'preparing a payment',
  prepare_purchase_order: 'preparing a purchase order',
  prepare_price_quote: 'pricing a quote',
  draft_customer_message: 'writing a draft',
  update_ticket_status: 'updating the ticket',
  ask_teammate: 'asking a teammate',
  final_result: 'writing the report',
}

export const money = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
