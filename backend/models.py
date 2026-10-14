"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]

AGENT_NAMES: tuple[str, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")

AGENT_TITLES: dict[str, str] = {
    "boss": "Boss",
    "inventory": "Inventory",
    "accounting": "Accounting",
    "facilities": "Facilities",
    "customer_service": "Customer Service",
}


# ---------------------------------------------------------------------------
# What each agent hands back
# ---------------------------------------------------------------------------

class AgentReport(BaseModel):
    """What a specialist returns to whoever delegated to it."""

    summary: str = Field(description="Two or three sentences: what you found and what you did.")
    facts: list[str] = Field(
        default_factory=list,
        description="Numbers and facts you used, each quoted from a tool result (e.g. 'M on hand: 8').",
    )
    actions: list[str] = Field(
        default_factory=list,
        description="Things you prepared or changed, with ids (e.g. 'payment request #1, $840, pending').",
    )
    needs_human: list[str] = Field(
        default_factory=list,
        description="Decisions only a human can make (approve request #N, confirm quote #N, send draft #N).",
    )
    open_questions: list[str] = Field(
        default_factory=list,
        description="Anything you could not find in the tools. Never fill these gaps with guesses.",
    )


class Contribution(BaseModel):
    agent: AgentName
    did: str = Field(description="One sentence on what this agent did on the ticket.")


class TicketResolution(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    final_status: Literal["resolved", "waiting_on_human", "in_progress"]
    outcome: str = Field(description="Two to four sentences a shop owner can read: what happens and why.")
    contributions: list[Contribution] = Field(description="One line per agent that worked on the ticket.")
    human_approvals_needed: list[str] = Field(
        default_factory=list, description="Each pending request or draft a human must act on, with id and amount."
    )
    cash_impact: str = Field(description="How checking changes if the human approves, with dollar amounts from the tools.")


# ---------------------------------------------------------------------------
# Run state shared by every agent in one ticket run
# ---------------------------------------------------------------------------

@dataclass
class Budget:
    """Hard limits for one ticket run, shared by all agents in it."""

    max_total_tokens: int = 120_000
    max_delegations: int = 10
    max_depth: int = 3
    tokens_used: int = 0
    delegations: int = 0

    def tokens_left(self) -> int:
        return max(self.max_total_tokens - self.tokens_used, 0)


@dataclass
class TeamDeps:
    """Passed to every agent run (PydanticAI deps)."""

    run_id: str
    ticket_id: int
    agent: str
    chain: list[str]                    # who delegated to whom, e.g. ["boss", "accounting"]
    budget: Budget
    usage_by_agent: dict[str, dict] = field(default_factory=dict)
    handoffs: list[dict] = field(default_factory=list)  # every delegation in this run, in order

    @property
    def depth(self) -> int:
        return len(self.chain) - 1

    def child(self, teammate: str) -> "TeamDeps":
        return TeamDeps(
            run_id=self.run_id,
            ticket_id=self.ticket_id,
            agent=teammate,
            chain=[*self.chain, teammate],
            budget=self.budget,
            usage_by_agent=self.usage_by_agent,
            handoffs=self.handoffs,
        )
