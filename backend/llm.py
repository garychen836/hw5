"""One place that builds the LLM for every agent.

Every agent in this homework must run on gpt-6-luna and nothing else, so the
model name is fixed here instead of read from settings.

Calls go straight to OpenAI with OPENAI_API_KEY. (The course Portkey key hit
its usage cap during this homework, so the project uses my own OpenAI key;
the model is still gpt-6-luna only.)

The key comes from the project's .env file when it exists (repo root, then
one level above). Keys already in the shell or app environment are ignored in
that case, so a stale key exported somewhere else can never beat the one in
.env. With no .env at all, the environment is used.
"""

import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = next((p for p in (ROOT / ".env", ROOT.parent / ".env") if p.exists()), None)
_SETTINGS = {k: v for k, v in dotenv_values(ENV_FILE).items() if v} if ENV_FILE else dict(os.environ)
for _k, _v in _SETTINGS.items():  # other settings (e.g. PYDANTIC_AI_NO_BANNER) still reach the process
    os.environ.setdefault(_k, _v)

MODEL_NAME = "gpt-6-luna"  # locked: the assignment allows no other model

# luna only calls tools when reasoning is off.
MODEL_SETTINGS = {"openai_reasoning_effort": "none"}


def key_source() -> str:
    """Which key the agents are using (always the OpenAI key)."""
    if _SETTINGS.get("OPENAI_API_KEY"):
        return "openai"
    raise RuntimeError("No API key found: set OPENAI_API_KEY in .env (see .env.example)")


def build_model() -> OpenAIChatModel:
    """The gpt-6-luna model every agent shares."""
    key_source()
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(api_key=_SETTINGS["OPENAI_API_KEY"]))
