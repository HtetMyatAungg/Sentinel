# Sentinel 60-second Demo Script

## Setup
- Launch app: `python.exe c:/Hackathon/Cusor/app.PY`
- Open local URL shown by Gradio.

## Flow (Financial Intelligence track)
1. Query: `Stripe`
   - Callout: "Strong positive profile and clear evidence."
   - Show verdict, confidence, and evidence rows.
2. Query: `Ravelin`
   - Callout: "Mixed/aging funding signals trigger escalation."
   - Show human-review banner and explain why.
3. Query: `Nonexistent Shell Co`
   - Callout: "No-match path escalates safely for manual investigation."
   - Show trace proving the guardrail path.

## Judge talking points
- "This is human-out-of-the-loop by default, with deterministic guardrails for hard-risk policy."
- "Every recommendation is schema-validated and evidence-cited."
- "Agent trace makes tool calls auditable and review-ready."
