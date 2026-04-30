"""Sentinel UI — counterparty risk terminal."""
import logging
import os
import threading
import time
from collections import OrderedDict

import gradio as gr # pyright: ignore[reportMissingImports]
from agent import run_agent
from Specter import warmup_specter_connection

logger = logging.getLogger("sentinel.ui")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

_ANALYSIS_CACHE: "OrderedDict[str, dict]" = OrderedDict()
_ANALYSIS_CACHE_MAX = 64


VERDICT_STYLES = {
    "PROCEED":  ("◆", "#10b981", "Auto-approved"),
    "ESCALATE": ("◇", "#f59e0b", "Human review required"),
    "DECLINE":  ("✕", "#ef4444", "Auto-declined"),
}

SEVERITY_GLYPH = {
    "POSITIVE": ("▲", "#10b981"),
    "NEUTRAL":  ("●", "#94a3b8"),
    "CONCERN":  ("▼", "#f59e0b"),
    "BLOCKER":  ("■", "#ef4444"),
}


CSS = """
.gradio-container {
    background:
        radial-gradient(1200px 600px at 10% -10%, rgba(16, 185, 129, 0.08), transparent 60%),
        radial-gradient(900px 500px at 100% 0%, rgba(59, 130, 246, 0.08), transparent 55%),
        #0a0e14 !important;
    font-family: 'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace !important;
    max-width: 1100px !important;
    margin: 0 auto !important;
    padding: 32px 20px 40px !important;
}
.gradio-container * { color: #e2e8f0; }

.gradio-main {
    background: #0c111b;
    border: 1px solid #1e293b;
    border-radius: 10px;
    box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
    padding: 28px;
    animation: rise-in 280ms ease-out;
}
.kpi-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin: 0 0 16px 0;
}
.kpi {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 10px 12px;
    transition: border-color 180ms ease, transform 180ms ease;
}
.kpi:hover {
    border-color: #334155;
    transform: translateY(-1px);
}
.kpi-label {
    font-size: 10px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #64748b;
}
.kpi-value {
    font-size: 13px;
    color: #e2e8f0;
    margin-top: 4px;
}

#header {
    border-bottom: 1px solid #1e293b;
    padding: 0 0 16px 0;
    margin-bottom: 24px;
}
#header h1 {
    font-size: 28px !important;
    letter-spacing: -0.02em;
    margin: 0 !important;
    color: #f8fafc !important;
    font-weight: 600;
}
#header .subtitle {
    color: #64748b;
    font-size: 12px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 4px;
}

#input-row { gap: 8px !important; }
#input-row textarea, #input-row input {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    color: #f1f5f9 !important;
    font-family: inherit !important;
    border-radius: 6px !important;
}
#submit-btn {
    background: #f8fafc !important;
    color: #0a0e14 !important;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-size: 12px !important;
    border: none !important;
}
#submit-btn:hover { background: #e2e8f0 !important; }
#submit-btn {
    transition: transform 120ms ease, box-shadow 120ms ease;
}
#submit-btn:active {
    transform: translateY(1px) scale(0.995);
}
#clear-btn {
    background: #0f172a !important;
    color: #cbd5e1 !important;
    border: 1px solid #334155 !important;
    font-size: 12px !important;
}
#clear-btn:hover { background: #111c31 !important; }
.status-pill {
    margin: 8px 0 0 0;
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    color: #94a3b8;
    animation: fade-in 180ms ease-out;
}

.gradio-container .examples {
    margin-top: 10px !important;
    margin-bottom: 14px !important;
}
.gradio-container .examples .example {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
    border-radius: 999px !important;
    color: #cbd5e1 !important;
}

.memo {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 24px;
    margin-top: 16px;
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    animation: rise-in 220ms ease-out;
}
.memo-header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 16px;
    margin-bottom: 16px;
}
.memo-entity {
    font-size: 20px;
    font-weight: 600;
    color: #f8fafc;
    letter-spacing: -0.01em;
}
.memo-domain { color: #64748b; font-size: 12px; margin-top: 2px; }
.memo-verdict {
    text-align: right;
    font-size: 11px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}
.verdict-glyph { font-size: 24px; line-height: 1; }
.verdict-label { font-weight: 700; margin-top: 4px; }
.verdict-sub { color: #64748b; font-size: 10px; margin-top: 2px; }

.confidence-bar {
    height: 2px;
    background: #1e293b;
    margin: 16px 0;
    position: relative;
    overflow: hidden;
}
.confidence-fill {
    height: 100%;
    background: linear-gradient(90deg, #f59e0b, #10b981);
    transition: width 360ms ease-out;
}
.confidence-label {
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: #64748b;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 4px;
}

.summary {
    color: #cbd5e1;
    font-size: 14px;
    line-height: 1.7;
    margin: 16px 0 24px 0;
    padding-left: 12px;
    border-left: 2px solid #334155;
    font-style: italic;
}

.section-label {
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #64748b;
    margin: 24px 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #1e293b;
}

.evidence-row {
    display: grid;
    grid-template-columns: 24px 140px 1fr;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #131a26;
    align-items: start;
    font-size: 13px;
}
.evidence-row:last-child { border-bottom: none; }
.evidence-glyph { font-size: 14px; line-height: 1.4; }
.evidence-field {
    color: #64748b;
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    padding-top: 1px;
}
.evidence-finding { color: #e2e8f0; line-height: 1.5; }
.evidence-raw {
    display: block;
    color: #475569;
    font-size: 11px;
    margin-top: 4px;
}

.review-banner {
    background: #1c1410;
    border: 1px solid #78350f;
    border-left: 3px solid #f59e0b;
    padding: 12px 16px;
    margin-top: 16px;
    font-size: 13px;
    color: #fed7aa;
}
.review-banner-label {
    font-size: 10px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #f59e0b;
    margin-bottom: 4px;
}

.trace {
    background: #060a10;
    border: 1px solid #131a26;
    padding: 12px;
    font-size: 11px;
    color: #475569;
    line-height: 1.6;
}
.trace-step { color: #64748b; }
.trace-tool { color: #94a3b8; font-weight: 600; }

@keyframes rise-in {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
}
"""


def render_memo(result: dict) -> str:
    memo = result["memo"]
    trace = result["trace"]

    glyph, color, sub = VERDICT_STYLES[memo["verdict"]]
    confidence_pct = int(memo["confidence"] * 100)

    domain_html = (
        f'<div class="memo-domain">{memo["domain"]}</div>' if memo.get("domain") else ""
    )

    review_html = ""
    if memo.get("requires_human_review") and memo.get("review_reason"):
        review_html = f"""
        <div class="review-banner">
            <div class="review-banner-label">Human Review Required</div>
            {memo["review_reason"]}
        </div>
        """

    evidence_rows = ""
    for ev in memo["evidence"]:
        sev_glyph, sev_color = SEVERITY_GLYPH[ev["severity"]]
        raw = (
            f'<span class="evidence-raw">{ev["raw_value"]}</span>'
            if ev.get("raw_value") else ""
        )
        evidence_rows += f"""
        <div class="evidence-row">
            <div class="evidence-glyph" style="color:{sev_color}">{sev_glyph}</div>
            <div class="evidence-field">{ev["field"]}</div>
            <div class="evidence-finding">{ev["finding"]}{raw}</div>
        </div>
        """

    trace_html = ""
    for t in trace:
        preview = t["result_preview"].replace("<", "&lt;").replace(">", "&gt;")
        trace_html += (
            f'<div><span class="trace-step">[{t["step"]:02d}]</span> '
            f'<span class="trace-tool">{t["tool"]}</span>'
            f'({", ".join(f"{k}={v!r}" for k, v in t["input"].items())})'
            f' → {preview[:120]}{"…" if len(preview) > 120 else ""}</div>'
        )

    return f"""
    <div class="memo">
        <div class="memo-header">
            <div>
                <div class="memo-entity">{memo["entity_name"]}</div>
                {domain_html}
            </div>
            <div class="memo-verdict">
                <div class="verdict-glyph" style="color:{color}">{glyph}</div>
                <div class="verdict-label" style="color:{color}">{memo["verdict"]}</div>
                <div class="verdict-sub">{sub}</div>
            </div>
        </div>

        <div class="confidence-label">
            <span>Confidence</span><span>{confidence_pct}%</span>
        </div>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width:{confidence_pct}%"></div>
        </div>

        <div class="summary">{memo["summary"]}</div>

        {review_html}

        <div class="section-label">Evidence ({len(memo["evidence"])})</div>
        {evidence_rows}

        <div class="section-label">Agent Trace</div>
        <div class="trace">{trace_html}</div>
    </div>
    """


def analyze(entity_name: str):
    if not entity_name or not entity_name.strip():
        return (
            '<div class="memo" style="color:#64748b">Enter a company name above.</div>',
            '<div class="status-pill">Type a company name to begin analysis.</div>',
        )
    try:
        started_at = time.perf_counter()
        normalized = entity_name.strip().lower()
        if normalized in _ANALYSIS_CACHE:
            result = _ANALYSIS_CACHE.pop(normalized)
            _ANALYSIS_CACHE[normalized] = result
            source = "cache hit"
        else:
            result = run_agent(entity_name.strip())
            _ANALYSIS_CACHE[normalized] = result
            if len(_ANALYSIS_CACHE) > _ANALYSIS_CACHE_MAX:
                _ANALYSIS_CACHE.popitem(last=False)
            source = "live analysis"
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        status = (
            f'<div class="status-pill">Completed in {elapsed_ms} ms ({source}). '
            f'Entity: <strong>{entity_name.strip()}</strong></div>'
        )
        return render_memo(result), status
    except Exception:
        logger.exception("Failed to analyze counterparty input")
        return (
            '<div class="memo" style="color:#ef4444">'
            "Analysis failed due to an internal error. Please retry or check server logs."
            "</div>",
            '<div class="status-pill">Run failed. Check logs and retry.</div>',
        )


def preview_status(entity_name: str) -> str:
    if not entity_name or not entity_name.strip():
        return '<div class="status-pill">Type a company name to begin analysis.</div>'
    trimmed = entity_name.strip()
    return f'<div class="status-pill">Ready to analyze <strong>{trimmed}</strong>. Press Enter or click Analyze.</div>'


with gr.Blocks(title="Sentinel - Counterparty Risk Terminal") as demo:
    with gr.Column(elem_classes="gradio-main"):
        with gr.Column(elem_id="header"):
            gr.HTML("""
                <h1>SENTINEL</h1>
                <div class="subtitle">Counterparty Risk · Human-out-of-the-loop</div>
            """)
        gr.HTML("""
            <div class="kpi-strip">
                <div class="kpi"><div class="kpi-label">Decision Engine</div><div class="kpi-value">PROCEED / ESCALATE / DECLINE</div></div>
                <div class="kpi"><div class="kpi-label">Evidence</div><div class="kpi-value">Field-level rationale + trace</div></div>
                <div class="kpi"><div class="kpi-label">Safety</div><div class="kpi-value">Deterministic policy guardrails</div></div>
            </div>
        """)

        with gr.Row(elem_id="input-row"):
            entity = gr.Textbox(
                placeholder="Enter company name (e.g. Stripe.com, Monzo.com, Ravelin.com)",
                label="",
                scale=5,
                container=False,
            )
            submit = gr.Button("Analyze", elem_id="submit-btn", scale=1)
            clear = gr.Button("Clear", elem_id="clear-btn", scale=1)

        status = gr.HTML('<div class="status-pill">Type a company name to begin analysis.</div>')

        gr.Examples(
            examples=["Stripe.com", "Monzo.com", "Ravelin.com", "Afterpay.com", "Nonexistent Shell Co"],
            inputs=entity,
            label="",
        )

        output = gr.HTML()

        submit.click(analyze, inputs=entity, outputs=[output, status])
        entity.submit(analyze, inputs=entity, outputs=[output, status])
        entity.change(preview_status, inputs=entity, outputs=status)
        clear.click(
            lambda: ("", "", '<div class="status-pill">Type a company name to begin analysis.</div>'),
            inputs=None,
            outputs=[entity, output, status],
        )

if __name__ == "__main__":
    # Allow override via env var; otherwise try ports 7860-7960.
    configured_port = os.getenv("GRADIO_SERVER_PORT")
    launch_kwargs = {
        "server_name": "0.0.0.0",
        "share": False,
        "css": CSS,
        "theme": gr.themes.Base(),
    }

    candidate_ports: list[int]
    if configured_port:
        preferred = int(configured_port)
        # Try configured port first, then fall back to standard sweep.
        candidate_ports = [preferred] + [p for p in range(7860, 7961) if p != preferred]
    else:
        candidate_ports = list(range(7860, 7961))

    last_error = None
    for port in candidate_ports:
        try:
            launch_kwargs["server_port"] = port
            threading.Thread(target=warmup_specter_connection, daemon=True).start()
            demo.launch(**launch_kwargs)
            break
        except OSError as err:
            last_error = err
            if "Cannot find empty port" in str(err) or "WinError 10048" in str(err):
                continue
            raise
    else:
        if configured_port:
            raise OSError(
                f"Unable to bind configured port {configured_port} or any fallback port in 7860-7960."
            ) from last_error
        raise OSError("Unable to bind any port in 7860-7960.") from last_error