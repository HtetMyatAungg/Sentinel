# Sentinel Final Demo Script (Best 2-3 Minutes)

## 0:00-0:20 - Opening Hook
"In high-risk finance workflows, speed without control is dangerous, and control without speed is expensive.

Sentinel solves this by turning a company name into a policy-safe decision in seconds: `PROCEED`, `ESCALATE`, or `DECLINE`, with evidence and full traceability."

## 0:20-0:30 - What To Watch
"As I demo, watch three things:
live intelligence retrieval, deterministic guardrails, and auditable decision reasoning."

## 0:30-1:10 - Case 1: Healthy Counterparty (`PROCEED`)
Action: Enter `Monzo` and click Analyze.

Say:
"Sentinel resolves the entity, pulls live company signals, and returns a structured risk memo.
Here it lands on `PROCEED`, with confidence and evidence tied to concrete fields such as operating status, funding recency, and growth indicators.
This is not a black-box answer; every claim is inspectable."

Point to:
- Verdict
- Confidence bar
- Evidence rows
- Agent trace

## 1:10-1:50 - Case 2: Policy-Sensitive Risk (`ESCALATE`)
Action: Enter `Afterpay` and click Analyze.

Say:
"Now we test a case where full automation would be risky.
Sentinel detects acquisition context and policy guardrails force `ESCALATE`.
So instead of pretending certainty, it explicitly routes to human review with a reason."

Point to:
- `ESCALATE` badge
- Human review reason
- Evidence supporting escalation

## 1:50-2:20 - Case 3: Unknown Entity (`DECLINE`)
Action: Enter `Nonexistent Shell Co` and click Analyze.

Say:
"When no verified company match exists, Sentinel hard-fails safely to `DECLINE`.
No entity resolution means no trustworthy risk assessment, so Sentinel refuses to fabricate confidence."

Point to:
- `DECLINE` verdict
- Explanation text
- Trace showing failed resolution

## 2:20-2:50 - Closing (Judge-Optimized)
"Sentinel is built for real financial operations:
live API-driven intelligence, deterministic safety rails, schema-validated outputs, and full audit trace.
It reduces analyst triage load while preserving control at the exact points where risk is ambiguous."

## 2:50-3:00 - Final Line
"Sentinel makes counterparty decisions faster, safer, and explainable by design."

## Fast Q&A Lines
- "How is this safe?" -> "Guardrails can deterministically override model output."
- "How is this trustworthy?" -> "Field-level evidence plus tool-call trace."
- "What if data is missing?" -> "Confidence drops and policy routes to safe outcomes."
- "What is the ROI?" -> "Faster triage, fewer manual reviews, better auditability."
