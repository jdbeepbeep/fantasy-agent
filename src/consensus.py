"""
Pulls expert consensus draft rankings (aggregated from sites like
FantasyPros, ESPN experts, etc.) via Claude's web search, once per
draft session rather than per-player -- a single research call covering
the whole player pool is far cheaper and faster than searching per pick.
"""
from __future__ import annotations
import json
import os
import re
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # ensures .env is loaded even if this module is imported
                # standalone, without going through src.config first


def normalize_name(name: str) -> str:
    """Loose matching key: lowercase, strip punctuation and suffixes."""
    name = name.lower()
    name = re.sub(r"\b(jr|sr|ii|iii|iv)\b\.?", "", name)
    name = re.sub(r"[^a-z0-9 ]", "", name)
    return " ".join(name.split())


def fetch_consensus_rankings(scoring_type: str, top_n: int = 150) -> dict:
    """
    Returns {normalized_player_name: overall_rank}. Ranks are 1 = best.
    Players not found in the returned dict simply weren't in the top_n
    consensus list (deep sleepers, rookies not widely ranked yet, etc.)
    -- callers should fall back to ESPN's own projection for those.
    """
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=180.0)

    prompt = f"""Search the web for current {scoring_type} fantasy football
expert consensus draft rankings for the upcoming season (aggregate
sources like FantasyPros consensus rankings, ESPN expert rankings, and
similar). Compile a single ranked list of the top {top_n} overall
players (all positions combined, ranked 1 to {top_n} by consensus
draft value).

Respond with ONLY a JSON array, no other text, no markdown code fences.
Each entry: {{"rank": <int>, "name": "<player full name>"}}
Example: [{{"rank": 1, "name": "Christian McCaffrey"}}, ...]"""

    # Streaming rather than a single blocking call -- this request runs
    # long enough (multiple searches + a large output) that non-streaming
    # requests are prone to being cut off by network infrastructure along
    # the way, even though the server is still working. Streaming keeps
    # the connection actively alive the whole time instead.
    text_parts = []
    with client.messages.stream(
        model="claude-sonnet-5",
        max_tokens=6000,
        messages=[{"role": "user", "content": prompt}],
        tools=[{"type": "web_search_20260318", "name": "web_search", "max_uses": 4}],
    ) as stream:
        for chunk in stream.text_stream:
            text_parts.append(chunk)

    text = "".join(text_parts)
    # Claude may still wrap in fences despite instructions -- strip defensively
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        entries = json.loads(text)
    except json.JSONDecodeError:
        # Try to salvage just the JSON array if there's stray text around it
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return {}
        entries = json.loads(match.group(0))

    return {normalize_name(e["name"]): e["rank"] for e in entries if "name" in e and "rank" in e}


def get_consensus_rank(player_name: str, rankings: dict) -> int | None:
    """Returns the consensus rank for a player, or None if unranked."""
    return rankings.get(normalize_name(player_name))
