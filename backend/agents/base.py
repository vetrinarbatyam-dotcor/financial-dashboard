"""
agents/base.py — Claude CLI caller (Claude Max subscription) for all OR Finance sub-agents.
"""

import asyncio
import json
import re

AGENT_RESPONSE_SCHEMA = {
    "score": "integer 0-100",
    "summary": "2-3 sentence analysis",
    "bullets": ["list of 5 key insight strings"],
    "warnings": ["list of red flag strings, may be empty"],
}

_FALLBACK_RESULT = {
    "score": 50,
    "summary": "Analysis unavailable due to Claude CLI error.",
    "bullets": [],
    "warnings": ["Claude CLI call failed"],
}


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in Claude response: {text[:200]}")
    return json.loads(text[start:end + 1])


def _validate_result(result: dict) -> dict:
    score = result.get("score", 50)
    if not isinstance(score, (int, float)):
        score = 50
    score = max(0, min(100, int(score)))

    summary = result.get("summary", "No summary provided.")
    if not isinstance(summary, str):
        summary = str(summary)

    bullets = result.get("bullets", [])
    if not isinstance(bullets, list):
        bullets = []
    bullets = [str(b) for b in bullets[:5]]

    warnings = result.get("warnings", [])
    if not isinstance(warnings, list):
        warnings = []
    warnings = [str(w) for w in warnings]

    return {"score": score, "summary": summary, "bullets": bullets, "warnings": warnings}


async def call_claude(system_prompt: str, user_prompt: str, data: dict) -> dict:
    """
    Calls Claude CLI (claude -p) using the Claude Max subscription.
    Returns a validated dict: { score, summary, bullets, warnings }
    """
    data_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    full_prompt = (
        f"SYSTEM: {system_prompt}\n\n"
        f"IMPORTANT: Write ALL text fields (summary, bullets, warnings) in Hebrew (עברית).\n\n"
        f"USER: {user_prompt}\n\n"
        f"STOCK DATA:\n{data_str}\n\n"
        f"Return ONLY a valid JSON object with these exact keys:\n"
        f'{{"score": <integer 0-100>, "summary": "<2-3 sentences in Hebrew>", '
        f'"bullets": ["<5 key insights in Hebrew>"], "warnings": ["<red flags in Hebrew>"]}}\n'
        f"No markdown fences, no extra text outside the JSON."
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", full_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        response_text = stdout.decode().strip()
        if not response_text:
            raise RuntimeError(f"Empty Claude response. stderr: {stderr.decode()[:200]}")
        result = _extract_json(response_text)
        return _validate_result(result)
    except asyncio.TimeoutError:
        return {**_FALLBACK_RESULT, "warnings": ["Claude CLI timeout (120s)"]}
    except Exception as exc:
        return {**_FALLBACK_RESULT, "warnings": [f"Claude CLI error: {str(exc)[:200]}"]}
