# Sentinel

> Autonomous counterparty risk agent for fintech operators.
> Built for **Cursor × Briefcase London 2026** · Track: **Financial Intelligence**

Sentinel decides whether to do business with a counterparty by gathering Specter intelligence and reasoning over funding, growth, and operating signals. It auto-approves clear PROCEEDs, auto-declines clear DECLINEs, and only escalates the genuinely uncertain cases to a human analyst — with structured evidence and a confidence score on every memo.

---

## The problem

Vendor onboarding, B2B credit, and counterparty due-diligence teams burn hours per entity hand-checking the same signals: are they a real company, who funds them, are they growing or dying, are they about to go bust. The work is structured, repetitive, and exactly the shape an agent should handle — *if* the agent knows when to stop and ask a human.

Most "AI for compliance" tools are chat wrappers: a human still drives every decision. Sentinel inverts that. The human is **out of the loop** by default, and the agent's job is to know when it shouldn't be.

## How it decides

```
                 ┌──────────────────┐
                 │  Company name    │
                 └────────┬─────────┘
                          ▼
              search_company (Specter)
                          ▼
                  ┌───────────────┐
              ┌───│  No match?    │── yes ──▶ ESCALATE (human)
              │   └───────────────┘
              no
              ▼
              enrich_company (Specter)
                          ▼
                  ┌───────────────────────┐
                  │  Heuristic gate       │
                  │  + LLM synthesis      │
                  └───────────┬───────────┘
                              ▼
            ┌─────────────────┼──────────────────┐
            ▼                 ▼                  ▼
        PROCEED           ESCALATE             DECLINE
       (autonomous)    (human review)        (autonomous)
```

The gate is encoded in the system prompt:

| Verdict | Trigger |
|---|---|
| **DECLINE** | `operating_status == closed` · OR brand-new entity with zero traction and no investors |
| **ESCALATE** | `acquired` (different decision tree) · OR `no_recent_funding` + headcount declining · OR mixed positive/negative signals · OR confidence < 0.65 · OR no Specter footprint |
| **PROCEED** | `active` + late/growth stage + (top-tier investors OR recent funding) + non-negative headcount trajectory |

Every memo ships with **3–5 evidence items**, each citing the exact Specter field that drove it.

## Architecture

```
   ┌─────────────┐    name     ┌──────────────────────┐
   │  Gradio UI  │────────────▶│  Anthropic Agent     │
   │  (terminal) │             │  Claude Sonnet 4.5   │
   └──────▲──────┘             └──────────┬───────────┘
          │ memo                          │ tool_use
          │                    ┌──────────┴──────────┐
          │                    ▼                     ▼
          │        search_company(name)    enrich_company(domain)
          │                    │                     │
          │                    ▼                     ▼
          │          ┌────────────────────────────────┐
          │          │       Specter API              │
          │          │  /entities  /companies         │
          │          └────────────────────────────────┘
          │                    │
          │                    ▼
          └────  CounterpartyMemo (Pydantic-validated)
                 ├─ verdict: PROCEED | ESCALATE | DECLINE
                 ├─ confidence: 0.0 – 1.0
                 ├─ evidence: [{severity, field, finding, raw_value}]
                 └─ requires_human_review: bool
```

## Demo

| Input | Verdict | Why |
|---|---|---|
| **Stripe** | ◆ PROCEED | Top-tier investors, late stage, headcount +11% YoY |
| **Monzo Bank** | ◆ PROCEED | FCA regulated, recent funding, headcount +25% |
| **Ravelin** | ◇ ESCALATE | Mixed: web traffic up but headcount −7%, no recent funding |
| **Nonexistent Shell Co** | ◇ ESCALATE | No Specter footprint — agent refuses to decide on missing data |

The fourth case is the human-out-of-the-loop story in one screen: when the data isn't there, the agent doesn't pretend.

## Run it

```bash
git clone https://github.com/HtetMyatAungg/Sentinel
cd Sentinel
pip install -r requirements.txt
cp .env.example .env  # add ANTHROPIC_API_KEY and SPECTER_API_KEY
python app.py         # → http://localhost:7860
```

CLI for testing:

```bash
python agent.py "Stripe"
```

Set `MOCK_MODE=1` to use bundled fixtures instead of live Specter calls.

## Files

| File | Purpose |
|---|---|
| `Schemas.py` | Pydantic models — `CounterpartyMemo`, `Evidence`, `Verdict`, `Severity` |
| `Specter.py` | Specter API client — `search_company`, `enrich_company`, mock fixtures |
| `Tools.py` | Anthropic tool-use schemas + dispatch table |
| `agent.py` | Tool-use loop with structured-output validation |
| `app.py` | Gradio UI — financial-terminal aesthetic |
| `tests/` | Smoke tests for Specter client and schemas |
| `DEMO_SCRIPT.md` | 90-second pitch script |

## Rubric mapping

**Track — Financial Intelligence.** Sentinel reads and interprets money signals (funding rounds, growth-stage classification, traction metrics, investor quality) to produce a confidence-weighted decision. The track question — *"how confident is the agent really, and which edge cases deserve a human eye?"* — is literally the agent's API surface: every memo carries a confidence score and a `requires_human_review` flag with a typed reason.

**Best use of Specter.** Two endpoints, real data flow. `text-search` resolves the user's plain-English company name to a domain; `enrichment` returns the full profile, which is slimmed to the 15 fields the agent actually reasons over (keeps the prompt tight, reduces token cost). The agent reasons over `highlights`, `growth_stage`, `traction_metrics.employee_count.12mo`, `funding.last_funding_date`, `operating_status`, `acquisition`, and `certifications`.

**Best use of Cursor.** Built live in Composer 2 in this session. The slim-profile pattern, the verdict heuristics, and the terminal-aesthetic UI were each iterated in Cursor.

**Best use of LLM models.** Claude Sonnet 4.5 in a tool-use loop with Pydantic-validated structured output. The system prompt encodes a deterministic verdict gate; the model's job is signal synthesis and evidence-citing, not policy. The agent emits exactly one JSON object per run, validated against `CounterpartyMemo` before it reaches the UI.

## What this would need for production

This is a 3-hour build. To take it past demoware:
- Add OFAC / UK HMT / EU sanctions and adverse-media as additional tools (the *real* compliance layer beneath the counterparty layer)
- Persist memos to an audit log with full agent trace — regulators will ask
- Confidence calibration: ground the 0–1 score against analyst feedback over time
- Multi-entity batch mode for portfolio screening
- The verdict heuristics are currently in-prompt; a hybrid approach (prompt + a thin rule engine) would be auditable and faster

## Built by

[@HtetMyatAungg](https://github.com/HtetMyatAungg) · solo · 3 hours · London, April 2026