"""Sentinel agent: tool-use loop that produces a structured CounterpartyMemo."""
import json
import os
from datetime import date, datetime
from typing import Dict, Any
from anthropic import Anthropic  # pyright: ignore[reportMissingImports]
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]
from Schemas import CounterpartyMemo
from Tools import TOOL_SCHEMAS, dispatch


load_dotenv()


def _create_anthropic_client() -> Anthropic:
    """Create an Anthropic client with a single, explicit auth method."""
    api_key = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
    auth_token = (os.getenv("ANTHROPIC_AUTH_TOKEN") or "").strip()

    if api_key:
        return Anthropic(api_key=api_key)
    if auth_token:
        return Anthropic(auth_token=auth_token)
    raise RuntimeError(
        "Missing Anthropic credentials. Set ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN in your environment or .env file."
    )


client: Anthropic | None = None
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")


SYSTEM_PROMPT = """You are Sentinel, an autonomous counterparty risk analyst for fintech operators.

Given a company name, your job is to gather signal and produce a verdict on whether to do business with them. You operate in a HUMAN-OUT-OF-THE-LOOP setting: the analyst should only get involved if you flag for review.

WORKFLOW (in order):
1. Call `search_company` to resolve the name to a domain.
2. If no domain match: stop. Verdict DECLINE, requires_human_review=false, reason null. Summary should state entity was not found in Specter and cannot be assessed.
3. Call `enrich_company` with that domain.
4. Analyze the profile against the heuristics below.
5. Output the final memo as a single JSON object — no preamble, no markdown fences.

HEURISTICS (apply in order; the first match wins):

DECLINE (do not proceed):
- operating_status == "closed"
- founded_year > current_year - 1 AND employee_count < 5 AND no investors

ESCALATE (human must review):
- operating_status == "acquired" — different decision tree, route to human
- "no_recent_funding" highlight AND last_funding_date older than 3 years AND headcount_12mo_change_pct negative
- Strong positive signals AND strong negative signals together (mixed)
- Confidence below 0.65 for any reason

PROCEED (auto-approve):
- operating_status == "active" AND growth_stage in {growth_stage, late_stage, exit_stage}
- AND ("top_tier_investors" in highlights OR last_funding within 24 months)
- AND headcount_12mo_change_pct >= 0 (or null with strong investor backing)

CONFIDENCE:
- Start at 0.9 if all key fields populated.
- Subtract 0.1 for each missing critical field (operating_status, growth_stage, employee_count, last_funding_date).
- Subtract 0.15 if highlights array is empty.

EVIDENCE:
- Produce 3 to 5 evidence items.
- Each MUST cite a specific Specter field name in the `field` attribute.
- Severity: POSITIVE (supports proceed), NEUTRAL (informational), CONCERN (supports escalate), BLOCKER (supports decline).
- raw_value should contain the actual data point (truncate to 80 chars).

OUTPUT SCHEMA (return EXACTLY this shape as JSON, no extra text):
{
  "entity_name": str,
  "domain": str | null,
  "verdict": "PROCEED" | "ESCALATE" | "DECLINE",
  "confidence": float between 0 and 1,
  "summary": str (2-3 sentences),
  "evidence": [
    {"severity": "POSITIVE|NEUTRAL|CONCERN|BLOCKER", "field": str, "finding": str, "raw_value": str|null}
  ],
  "requires_human_review": bool,
  "review_reason": str | null
}

Be specific. Cite numbers. The analyst's trust depends on you showing your work."""


def _parse_iso_date(value: Any) -> date | None:
    """Parse YYYY-MM-DD strings to date, returning None on invalid input."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _confidence_penalty(profile: Dict[str, Any]) -> float:
    """Apply deterministic confidence penalties from missing critical fields."""
    penalties = 0.0
    critical_fields = (
        "operating_status",
        "growth_stage",
        "employee_count",
    )
    for field in critical_fields:
        if profile.get(field) is None:
            penalties += 0.1
    if (profile.get("funding") or {}).get("last_funding_date") is None:
        penalties += 0.1
    if not profile.get("highlights"):
        penalties += 0.15
    return penalties


def enforce_policy_guardrails(memo_dict: Dict[str, Any], profile: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Deterministically enforce high-risk policy decisions outside the model.

    This guarantees that hard rules always win, even if model output drifts.
    """
    if not profile:
        return memo_dict

    forced_verdict = None
    forced_reason = None
    operating_status = profile.get("operating_status")
    founded_year = profile.get("founded_year")
    employee_count = profile.get("employee_count")
    investor_count = profile.get("investor_count")
    highlights = profile.get("highlights") or []
    funding = profile.get("funding") or {}
    last_funding_date = _parse_iso_date(funding.get("last_funding_date"))
    headcount_change = profile.get("headcount_12mo_change_pct")

    today = date.today()
    if operating_status == "closed":
        forced_verdict = "DECLINE"
        forced_reason = "Operating status is closed."
    elif isinstance(founded_year, int) and founded_year > today.year - 1 and (employee_count or 0) < 5 and (investor_count or 0) == 0:
        forced_verdict = "DECLINE"
        forced_reason = "Very new company with tiny headcount and no investors."
    elif operating_status == "acquired":
        forced_verdict = "ESCALATE"
        forced_reason = "Operating status is acquired; requires manual diligence."
    elif "no_recent_funding" in highlights and last_funding_date and (today - last_funding_date).days > 365 * 3 and isinstance(headcount_change, (int, float)) and headcount_change < 0:
        forced_verdict = "ESCALATE"
        forced_reason = "No recent funding plus shrinking headcount."

    proceed_signals = 0
    concern_signals = 0
    if "top_tier_investors" in highlights:
        proceed_signals += 1
    if last_funding_date and (today - last_funding_date).days <= 365 * 2:
        proceed_signals += 1
    if isinstance(headcount_change, (int, float)) and headcount_change > 0:
        proceed_signals += 1
    if "no_recent_funding" in highlights:
        concern_signals += 1
    if isinstance(headcount_change, (int, float)) and headcount_change < 0:
        concern_signals += 1
    if operating_status in {"closed", "acquired"}:
        concern_signals += 1

    if proceed_signals >= 2 and concern_signals >= 2:
        forced_verdict = "ESCALATE"
        forced_reason = "Mixed high positive and high negative signals."

    if memo_dict.get("confidence", 0.0) < 0.65:
        forced_verdict = "ESCALATE"
        forced_reason = "Confidence below 0.65."

    base_confidence = memo_dict.get("confidence", 0.0)
    if isinstance(base_confidence, (int, float)):
        adjusted = max(0.0, min(1.0, float(base_confidence) - _confidence_penalty(profile)))
        memo_dict["confidence"] = round(adjusted, 2)
    else:
        memo_dict["confidence"] = 0.5

    if forced_verdict:
        memo_dict["verdict"] = forced_verdict
        memo_dict["requires_human_review"] = forced_verdict == "ESCALATE"
        if forced_reason:
            memo_dict["review_reason"] = forced_reason if memo_dict["requires_human_review"] else None
    return memo_dict


def _is_unresolved_entity(trace: list[Dict[str, Any]], last_enrichment: Dict[str, Any] | None) -> bool:
    """Return True when search resolved no domain and no enrichment exists."""
    return last_enrichment is None and any(
        t.get("tool") == "search_company"
        and isinstance(t.get("result_preview"), str)
        and '"domain": null' in t["result_preview"]
        for t in trace
    )


def run_agent(entity_name: str, max_iterations: int = 8) -> Dict[str, Any]:
    """Run the tool-use loop until the model emits the final memo JSON."""
    global client
    if client is None:
        client = _create_anthropic_client()

    messages = [
        {"role": "user", "content": f"Produce a counterparty risk memo for: {entity_name}"}
    ]

    trace = []  # for the UI to show what the agent did
    last_enrichment: Dict[str, Any] | None = None

    for i in range(max_iterations):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str = dispatch(block.name, block.input)
                    if block.name == "enrich_company":
                        try:
                            parsed = json.loads(result_str)
                            if isinstance(parsed, dict) and "error" not in parsed:
                                last_enrichment = parsed
                        except json.JSONDecodeError:
                            last_enrichment = None
                    trace.append({
                        "step": i + 1,
                        "tool": block.name,
                        "input": block.input,
                        "result_preview": result_str[:300],
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
            messages.append({"role": "user", "content": tool_results})
            continue

        # Final answer
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        # Strip code fences if model adds them despite instructions
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.rsplit("```", 1)[0].strip()

        memo_dict = json.loads(text)

        # Hard-fail unknown entities: if search_company returns no domain and we never
        # receive a valid enrichment profile, we cannot perform automated diligence.
        unresolved_entity = _is_unresolved_entity(trace, last_enrichment)
        if unresolved_entity:
            memo_dict["verdict"] = "DECLINE"
            memo_dict["requires_human_review"] = False
            memo_dict["review_reason"] = None

        memo_dict = enforce_policy_guardrails(memo_dict, last_enrichment)
        memo = CounterpartyMemo(**memo_dict)
        return {"memo": memo.model_dump(), "trace": trace}

    raise RuntimeError(f"Agent exceeded {max_iterations} iterations without producing a memo")


if __name__ == "__main__":
    import sys
    name = " ".join(sys.argv[1:]) or "Stripe"
    result = run_agent(name)
    print(json.dumps(result, indent=2, default=str))