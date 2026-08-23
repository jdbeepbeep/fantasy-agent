"""
Uses Claude's web search tool to pull in real, current information --
injury news beyond ESPN's status field, expert takes, and matchup
context -- rather than relying on ESPN's own (often generic) data.

Note: each call here costs a bit more than a plain Claude API call,
since web search is billed per-search in addition to tokens. Used
deliberately (injury alerts, genuinely close lineup calls), not on
every single check.
"""
from __future__ import annotations
import os
from anthropic import Anthropic


def _run_research(prompt: str, max_searches: int = 3) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=90.0)
    try:
        # Streaming rather than a blocking call -- web-search requests can
        # run long enough that non-streaming calls are prone to being cut
        # off by network infrastructure mid-request. This also means one
        # slow/failed research call can't hang the whole monitoring run
        # (which matters since this runs unattended in GitHub Actions).
        text_parts = []
        with client.messages.stream(
            model="claude-sonnet-5",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
            tools=[{"type": "web_search_20260318", "name": "web_search", "max_uses": max_searches}],
        ) as stream:
            for chunk in stream.text_stream:
                text_parts.append(chunk)
        return "".join(text_parts)
    except Exception as e:
        # Research is a nice-to-have enrichment, not critical -- if it
        # fails (timeout, API error), skip it rather than crash the
        # whole monitor run over one missing news blurb.
        print(f"Research call failed (skipping this enrichment): {e}")
        return ""


def get_injury_context(player_name: str, team: str, status: str) -> str:
    """
    Searches for the most current news on an injured player -- practice
    reports, beat reporter updates, likely game status -- beyond ESPN's
    single-word status label.
    """
    prompt = (
        f"Search for the most recent news (last 48 hours) on NFL player "
        f"{player_name} ({team}), currently listed as {status}. "
        f"In 2-3 short sentences: what's the latest on their status and "
        f"likelihood of playing this week? Be concise, no preamble."
    )
    return _run_research(prompt)


def get_close_call_analysis(player_a: str, player_b: str, position: str, week: int) -> str:
    """
    For a genuinely close start/sit decision, searches for expert
    consensus and matchup context to help break the tie.
    """
    prompt = (
        f"I'm deciding between starting {player_a} or {player_b} "
        f"({position}) in fantasy football week {week}. Search for "
        f"current expert rankings/start-sit advice and matchup context "
        f"(opposing defense, recent form) for both. Give a direct "
        f"recommendation in 2-3 sentences, no preamble."
    )
    return _run_research(prompt)
