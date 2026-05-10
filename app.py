# app.py
# ══════════════════════════════════════════════════════
# DOSSIER-AGENT — STREAMLIT WEB APPLICATION
#
# Run with: streamlit run app.py
# ══════════════════════════════════════════════════════

import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from dossier_agent.graph  import dossier_graph
from dossier_agent.state  import DossierState
from dossier_agent.config import RISK_ICONS, VERDICT_ICONS, OUTPUTS_DIR


# ══════════════════════════════════════════════════════
# PAGE CONFIG — must be first Streamlit call
# ══════════════════════════════════════════════════════

st.set_page_config(
    page_title = "Dossier-Agent",
    page_icon  = "🕵️",
    layout     = "wide"
)


# ══════════════════════════════════════════════════════
# CUSTOM CSS
# ══════════════════════════════════════════════════════

st.markdown("""
<style>
  /* ── Base ── */
  .stApp { background-color: #0d1117; color: #e6edf3; }

  /* ── Hide Streamlit chrome ── */
  #MainMenu, footer, header { visibility: hidden; }

  /* ── Node status cards ── */
  .node-card {
    padding      : 10px 16px;
    border-radius: 8px;
    margin       : 4px 0;
    font-size    : 14px;
    border-left  : 4px solid #30363d;
    background   : #161b22;
  }
  .node-waiting  { border-left-color: #30363d; color: #8b949e; }
  .node-running  { border-left-color: #d29922; color: #f0d060; }
  .node-done     { border-left-color: #3fb950; color: #7ee787; }
  .node-skipped  { border-left-color: #58a6ff; color: #79c0ff; }
  .node-failed   { border-left-color: #f85149; color: #ff7b72; }

  /* ── Risk badges ── */
  .risk-LOW    { background:#0d2e1a; color:#3fb950;
                 padding:4px 14px; border-radius:12px;
                 font-weight:bold; font-size:15px; }
  .risk-MEDIUM { background:#2e1f00; color:#d29922;
                 padding:4px 14px; border-radius:12px;
                 font-weight:bold; font-size:15px; }
  .risk-HIGH   { background:#2e0d0d; color:#f85149;
                 padding:4px 14px; border-radius:12px;
                 font-weight:bold; font-size:15px; }

  /* ── Stat cards ── */
  .stat-card {
    background   : #161b22;
    border       : 1px solid #30363d;
    border-radius: 10px;
    padding      : 16px;
    text-align   : center;
  }
  .stat-value { font-size:28px; font-weight:bold; color:#58a6ff; }
  .stat-label { font-size:12px; color:#8b949e; margin-top:4px; }

  /* ── Fact cards ── */
  .fact-card {
    background   : #161b22;
    border-left  : 3px solid #58a6ff;
    border-radius: 6px;
    padding      : 10px 14px;
    margin       : 6px 0;
    font-size    : 14px;
  }

  /* ── Tag pills ── */
  .tag-pill {
    display      : inline-block;
    background   : #21262d;
    border       : 1px solid #30363d;
    border-radius: 20px;
    padding      : 3px 12px;
    margin       : 3px;
    font-size    : 13px;
    color        : #79c0ff;
  }

  /* ── Section headers ── */
  .section-header {
    font-size    : 13px;
    font-weight  : bold;
    color        : #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin       : 16px 0 8px 0;
    border-bottom: 1px solid #21262d;
    padding-bottom: 4px;
  }

  /* ── Routing badge ── */
  .route-badge {
    display      : inline-block;
    background   : #1c2128;
    border       : 1px solid #30363d;
    border-radius: 6px;
    padding      : 2px 10px;
    font-size    : 12px;
    color        : #d2a8ff;
    font-family  : monospace;
  }

  /* ── Input box ── */
  .stTextInput > div > div > input {
    background   : #161b22;
    color        : #e6edf3;
    border       : 1px solid #30363d;
    border-radius: 8px;
    font-size    : 16px;
  }

  /* ── History items ── */
  .history-item {
    background   : #161b22;
    border-radius: 8px;
    padding      : 10px;
    margin       : 6px 0;
    font-size    : 13px;
    border       : 1px solid #21262d;
  }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════

def node_card(label: str, status: str, detail: str = "") -> str:
    icons = {
        "waiting": "⬜",
        "running": "⏳",
        "done"   : "✅",
        "skipped": "⏭️",
        "failed" : "❌"
    }
    icon = icons.get(status, "•")
    det  = f"<br><small style='color:#8b949e'>{detail}</small>" if detail else ""
    return f"""
    <div class='node-card node-{status}'>
      {icon} <b>{label}</b>{det}
    </div>"""


def risk_badge(level: str) -> str:
    icon = RISK_ICONS.get(level, "⚪")
    return f"<span class='risk-{level}'>{icon} {level}</span>"


def stat_card(value: str, label: str) -> str:
    return f"""
    <div class='stat-card'>
      <div class='stat-value'>{value}</div>
      <div class='stat-label'>{label}</div>
    </div>"""


def load_history() -> list:
    """Load all saved JSON dossiers from outputs/."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    files   = sorted(
        [f for f in os.listdir(OUTPUTS_DIR) if f.endswith(".json")],
        reverse=True
    )[:15]

    history = []
    for f in files:
        try:
            with open(f"{OUTPUTS_DIR}/{f}", encoding="utf-8") as fp:
                history.append(json.load(fp))
        except Exception:
            pass
    return history


# ══════════════════════════════════════════════════════
# NODE TRACKER
# Shows live status of each node during pipeline
# ══════════════════════════════════════════════════════

NODE_LABELS = {
    "intake_node"   : "1. Intake & Planning",
    "planner_node"  : "2. Tool Planner",
    "tools_node"    : "3. Search Tools",
    "grader_node"   : "4. Quality Grader",
    "enricher_node" : "4b. Enricher",
    "analyst_node"  : "5. Deep Analyst",
    "writer_node"   : "6. Report Writer",
    "saver_node"    : "7. Save Results"
}


class NodeTracker:
    """
    Wraps the LangGraph graph to intercept node
    executions and update Streamlit UI in real-time.
    """

    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.statuses    = {k: "waiting" for k in NODE_LABELS}
        self.details     = {k: ""        for k in NODE_LABELS}
        self.current     = None
        self._render()

    def _render(self):
        html = "<div style='padding:4px'>"
        for node_id, label in NODE_LABELS.items():
            status = self.statuses[node_id]
            detail = self.details[node_id]
            html  += node_card(label, status, detail)
        html += "</div>"
        self.placeholder.markdown(html, unsafe_allow_html=True)

    def start(self, node_id: str):
        if self.current:
            self.statuses[self.current] = "done"
        self.current             = node_id
        self.statuses[node_id]   = "running"
        self.details[node_id]    = "Working..."
        self._render()

    def done(self, node_id: str, detail: str = ""):
        self.statuses[node_id] = "done"
        self.details[node_id]  = detail
        self._render()

    def skip(self, node_id: str, detail: str = ""):
        self.statuses[node_id] = "skipped"
        self.details[node_id]  = detail
        self._render()

    def finish_all(self):
        if self.current:
            self.statuses[self.current] = "done"
        self._render()


# ══════════════════════════════════════════════════════
# PIPELINE RUNNER
# Runs the graph and updates UI node by node
# ══════════════════════════════════════════════════════

def run_pipeline(subject: str, tracker: NodeTracker) -> tuple[dict, float]:
    """
    Runs dossier_graph with stream() to track
    which node is executing at each step.
    """

    initial: DossierState = {
        "subject"          : subject,
        "subject_type"     : "",
        "research_angles"  : [],
        "complexity"       : "",
        "search_queries"   : [],
        "raw_findings"     : [],
        "errors"           : [],
        "search_count"     : 0,
        "loop_count"       : 0,
        "quality_score"    : 0,
        "routing_decision" : "",
        "quality_gaps"     : [],
        "analyst_output"   : None,
        "final_report"     : None,
        "status"           : "",
        "output_path"      : ""
    }

    start       = time.time()
    final_state = {}

    # .stream() yields one dict per node execution
    # key = node name, value = what that node returned
    for step in dossier_graph.stream(initial):
        node_name = list(step.keys())[0]
        node_out  = step[node_name]

        # Update tracker
        tracker.start(node_name)

        # Build detail string from node output
        detail = ""
        if node_name == "intake_node":
            t      = node_out.get("subject_type", "?")
            c      = node_out.get("complexity",   "?")
            detail = f"Type: {t} | Complexity: {c}"

        elif node_name == "planner_node":
            q      = node_out.get("search_queries", [])
            detail = f"{len(q)} queries planned"

        elif node_name == "tools_node":
            f      = node_out.get("raw_findings", [])
            detail = f"{len(f)} tool results"

        elif node_name == "grader_node":
            sc     = node_out.get("quality_score",    "?")
            rd     = node_out.get("routing_decision", "?")
            detail = f"Score: {sc}/100 → {rd}"

        elif node_name == "enricher_node":
            detail = "Gap filled with deep search"

        elif node_name == "analyst_node":
            ao     = node_out.get("analyst_output")
            rl     = ao.risk_level if ao else "?"
            detail = f"Risk: {rl}"

        elif node_name == "writer_node":
            fr     = node_out.get("final_report")
            conf   = fr.confidence if fr else "?"
            detail = f"Confidence: {conf}/100"

        elif node_name == "saver_node":
            op     = node_out.get("output_path", "")
            detail = f"Saved ✅" if op else "Save skipped"

        tracker.done(node_name, detail)

        # Accumulate final state
        final_state.update(node_out)

    tracker.finish_all()

    # Re-run invoke to get complete final state
    # (stream only gives per-node diffs)
    complete = dossier_graph.invoke(initial)
    elapsed  = round(time.time() - start, 1)

    return complete, elapsed


# ══════════════════════════════════════════════════════
# REPORT DISPLAY
# Renders the DossierReport in a rich UI
# ══════════════════════════════════════════════════════

def display_report(result: dict, elapsed: float):
    report = result.get("final_report")
    status = result.get("status", "unknown")

    if not report:
        st.error("❌ No report was generated.")
        return

    # ── Top metrics bar ──────────────────────────────
    st.markdown("---")
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(
            stat_card(f"{report.confidence}%", "Confidence"),
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            stat_card(report.risk_level, "Risk Level"),
            unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            stat_card(str(report.sources_used), "Sources"),
            unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            stat_card(str(report.searches_performed), "Searches"),
            unsafe_allow_html=True
        )
    with c5:
        st.markdown(
            stat_card(f"{elapsed}s", "Time"),
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Subject header ────────────────────────────────
    st.markdown(f"""
    <h2 style='color:#e6edf3; margin-bottom:4px;'>
        {report.subject}
    </h2>
    <div style='color:#8b949e; font-size:14px; margin-bottom:12px;'>
        {report.subject_type.upper()}
        &nbsp;|&nbsp;
        {risk_badge(report.risk_level)}
        &nbsp;|&nbsp;
        <span style='color:#{"3fb950" if status=="complete" else "d29922"}'>
            {VERDICT_ICONS.get(status,"📋")} {status.upper()}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Two column layout ─────────────────────────────
    left, right = st.columns([3, 2])

    # ── LEFT COLUMN ───────────────────────────────────
    with left:

        # Overview
        st.markdown(
            "<div class='section-header'>📋 Overview</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='color:#c9d1d9; line-height:1.7'>"
            f"{report.overview}</div>",
            unsafe_allow_html=True
        )

        # Key facts
        st.markdown(
            "<div class='section-header'>🔑 Key Facts</div>",
            unsafe_allow_html=True
        )
        for i, fact in enumerate(report.key_facts, 1):
            st.markdown(
                f"<div class='fact-card'>"
                f"<b style='color:#58a6ff'>{i}.</b> {fact}"
                f"</div>",
                unsafe_allow_html=True
            )

        # Notable events
        if report.notable_events:
            st.markdown(
                "<div class='section-header'>📅 Notable Events</div>",
                unsafe_allow_html=True
            )
            for event in report.notable_events:
                st.markdown(f"• {event}")

    # ── RIGHT COLUMN ──────────────────────────────────
    with right:

        # Risk assessment
        st.markdown(
            "<div class='section-header'>⚠️ Risk Assessment</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            risk_badge(report.risk_level),
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='color:#8b949e; font-size:13px; margin-top:8px;'>"
            f"{report.risk_reason}</div>",
            unsafe_allow_html=True
        )

        if report.risk_factors:
            st.markdown("<br>**Risk Factors:**")
            for rf in report.risk_factors:
                st.markdown(
                    f"<div style='color:#f85149; font-size:13px;'>"
                    f"⚠️ {rf}</div>",
                    unsafe_allow_html=True
                )

        # Key relationships
        if report.key_relationships:
            st.markdown(
                "<div class='section-header'>🔗 Key Relationships</div>",
                unsafe_allow_html=True
            )
            for rel in report.key_relationships:
                st.markdown(
                    f"<div style='color:#79c0ff; font-size:13px;'>"
                    f"🔗 {rel}</div>",
                    unsafe_allow_html=True
                )

        # Tags
        st.markdown(
            "<div class='section-header'>🏷️ Tags</div>",
            unsafe_allow_html=True
        )
        tags_html = "".join([
            f"<span class='tag-pill'>#{t}</span>"
            for t in report.tags
        ])
        st.markdown(tags_html, unsafe_allow_html=True)

        # Graph stats
        st.markdown(
            "<div class='section-header'>📊 Graph Stats</div>",
            unsafe_allow_html=True
        )
        rd = result.get("routing_decision", "write")
        qs = result.get("quality_score",    0)
        er = len(result.get("errors", []))

        st.markdown(f"""
        <div style='font-size:13px; color:#8b949e; line-height:2'>
          🔀 Final routing &nbsp;:
          <span class='route-badge'>{rd}</span><br>
          📊 Quality score &nbsp;: <b style='color:#e6edf3'>{qs}/100</b><br>
          ⚠️  Errors caught &nbsp;: <b style='color:#e6edf3'>{er}</b><br>
          🔄 Search loops &nbsp;&nbsp;:
          <b style='color:#e6edf3'>{result.get("loop_count", 0)}</b>
        </div>
        """, unsafe_allow_html=True)

    # ── Download ──────────────────────────────────────
    st.markdown("---")

    payload = {
        "timestamp" : datetime.now().isoformat(),
        "subject"   : report.subject,
        "status"    : status,
        "report"    : report.model_dump(),
        "graph_stats": {
            "searches"      : report.searches_performed,
            "quality_score" : result.get("quality_score", 0),
            "routing"       : rd
        }
    }

    col_dl, col_saved = st.columns([1, 3])
    with col_dl:
        st.download_button(
            label     = "💾 Download JSON Report",
            data      = json.dumps(payload, indent=2),
            file_name = f"dossier_{report.subject.replace(' ','_')}.json",
            mime      = "application/json",
            use_container_width=True
        )
    with col_saved:
        if result.get("output_path"):
            st.success(
                f"✅ Auto-saved: `{result['output_path']}`"
            )


# ══════════════════════════════════════════════════════
# SIDEBAR — History
# ══════════════════════════════════════════════════════

def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <h3 style='color:#e6edf3; margin-bottom:4px;'>
            🕵️ Dossier-Agent
        </h3>
        <p style='color:#8b949e; font-size:12px; margin-top:0;'>
            LangGraph Multi-Agent System
        </p>
        <hr style='border-color:#21262d'>
        """, unsafe_allow_html=True)

        # About section
        with st.expander("ℹ️ How it works"):
            st.markdown("""
**8-node LangGraph pipeline:**

1. **Intake** — classifies subject + plans research
2. **Planner** — picks tools + writes queries  
3. **Tools** — runs web searches
4. **Grader** — scores quality → routes decision
5. **Enricher** — fills gaps *(if needed)*
6. **Analyst** — deep risk analysis
7. **Writer** — Pydantic structured report
8. **Saver** — saves to JSON history

Built with LangChain + LangGraph + Groq
            """)

        st.markdown("### 📁 Recent Dossiers")

        history = load_history()

        if not history:
            st.caption("No dossiers yet. Run your first one!")
            return

        for item in history:
            report  = item.get("report", {})
            subject = item.get("subject", "Unknown")
            ts      = item.get("timestamp", "")
            verdict = item.get("status", "?")
            risk    = report.get("risk_level", "?")
            conf    = report.get("confidence", "?")

            risk_icon    = RISK_ICONS.get(risk, "⚪")
            verdict_icon = VERDICT_ICONS.get(verdict, "📋")

            with st.expander(
                f"{risk_icon} {subject[:25]}{'...' if len(subject)>25 else ''}"
            ):
                st.markdown(f"""
                <div class='history-item'>
                  <div style='color:#e6edf3; font-weight:bold;'>
                    {subject}
                  </div>
                  <div style='color:#8b949e; font-size:12px; margin-top:4px;'>
                    {verdict_icon} {verdict.upper()} &nbsp;|&nbsp;
                    {risk_icon} {risk} &nbsp;|&nbsp;
                    📊 {conf}%
                  </div>
                  <div style='color:#6e7681; font-size:11px; margin-top:2px;'>
                    🕐 {ts}
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Show key facts from history
                facts = report.get("key_facts", [])[:3]
                if facts:
                    st.markdown("**Top facts:**")
                    for f in facts:
                        st.markdown(
                            f"<div style='font-size:12px; color:#8b949e;'>"
                            f"• {f[:80]}{'...' if len(f)>80 else ''}"
                            f"</div>",
                            unsafe_allow_html=True
                        )


# ══════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════

def main():

    render_sidebar()

    # ── Header ────────────────────────────────────────
    st.markdown("""
    <div style='text-align:center; padding: 20px 0 10px 0;'>
      <h1 style='color:#e6edf3; font-size:2.8em; margin-bottom:4px;'>
        🕵️ Dossier-Agent
      </h1>
      <p style='color:#8b949e; font-size:1.1em; margin:0;'>
        AI-Powered Intelligence Dossier Generator
      </p>
      <p style='color:#6e7681; font-size:0.85em; margin-top:6px;'>
        LangGraph · LangChain · Groq LLaMA 3.3 · Tavily
      </p>
    </div>
    <hr style='border-color:#21262d; margin: 10px 0 20px 0;'>
    """, unsafe_allow_html=True)

    # ── How it works bar ──────────────────────────────
    with st.expander("💡 How it works — click to expand"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("""
            **🧠 Plan**
            Intake node classifies your subject and builds a tailored research plan.
            """)
        with c2:
            st.markdown("""
            **🔍 Search**
            5 specialized tools search different angles — news, risk, financials, deep.
            """)
        with c3:
            st.markdown("""
            **⚖️ Grade & Route**
            Quality grader scores findings and dynamically routes to enrich or write.
            """)
        with c4:
            st.markdown("""
            **📋 Report**
            Analyst + Writer produce a validated Pydantic dossier with risk scoring.
            """)

    # ── Input section ─────────────────────────────────
    st.markdown("### 🔎 Enter a Subject to Research")

    col_in, col_btn = st.columns([5, 1])
    with col_in:
        subject = st.text_input(
            label            = "subject_input",
            placeholder      = 'e.g.  "Sam Altman"  or  "Mistral AI"',
            label_visibility = "collapsed"
        )
    with col_btn:
        run_btn = st.button(
            "🕵️ Research",
            type                = "primary",
            use_container_width = True
        )

    # ── Quick examples ────────────────────────────────
    st.markdown("**Quick examples:**")
    ex1, ex2, ex3, ex4, ex5 = st.columns(5)

    examples = [
        ("👤 Sam Altman",    "Sam Altman"),
        ("🏢 Mistral AI",    "Mistral AI"),
        ("👤 Yann LeCun",    "Yann LeCun"),
        ("🏢 Perplexity AI", "Perplexity AI"),
        ("👤 Demis Hassabis","Demis Hassabis"),
    ]

    for col, (label, value) in zip([ex1,ex2,ex3,ex4,ex5], examples):
        with col:
            if st.button(label, use_container_width=True):
                subject = value
                run_btn = True

    # ── Run the pipeline ──────────────────────────────
    if run_btn and subject:

        st.markdown("---")

        # Two column layout: tracker left, status right
        track_col, status_col = st.columns([2, 3])

        with track_col:
            st.markdown("### ⚙️ Pipeline")
            node_placeholder = st.empty()
            tracker          = NodeTracker(node_placeholder)

        with status_col:
            st.markdown("### 📡 Live Status")
            progress   = st.progress(0, text="Initializing...")
            status_box = st.empty()
            status_box.info(f"🚀 Starting research on: **{subject}**")

        # Progress updates alongside node tracking
        progress.progress(10, text="Intake & Planning...")

        try:
            # ── Run Pipeline ──────────────────────────
            # We run invoke() directly for simplicity
            # tracker updates via node prints in terminal
            # For true live UI we use stream()

            start_t = time.time()

            # Stream through nodes
            initial: DossierState = {
                "subject"          : subject,
                "subject_type"     : "",
                "research_angles"  : [],
                "complexity"       : "",
                "search_queries"   : [],
                "raw_findings"     : [],
                "errors"           : [],
                "search_count"     : 0,
                "loop_count"       : 0,
                "quality_score"    : 0,
                "routing_decision" : "",
                "quality_gaps"     : [],
                "analyst_output"   : None,
                "final_report"     : None,
                "status"           : "",
                "output_path"      : ""
            }

            node_progress = {
                "intake_node"   : (20,  "🧠 Intake done — planning research..."),
                "planner_node"  : (30,  "📋 Plan ready — selecting tools..."),
                "tools_node"    : (50,  "🔍 Searches complete — grading quality..."),
                "grader_node"   : (60,  "⚖️ Graded — routing decision made..."),
                "enricher_node" : (70,  "🔬 Enrichment complete..."),
                "analyst_node"  : (80,  "🧩 Analysis done — writing report..."),
                "writer_node"   : (90,  "✍️ Report written — saving..."),
                "saver_node"    : (100, "✅ Complete!")
            }

            final_result = None

            for step in dossier_graph.stream(initial):
                node_name = list(step.keys())[0]
                node_out  = step[node_name]

                # Update node tracker
                tracker.start(node_name)

                # Build detail for this node
                detail = ""
                if node_name == "intake_node":
                    t      = node_out.get("subject_type", "?")
                    c      = node_out.get("complexity",   "?")
                    detail = f"Type: {t} | {c}"
                elif node_name == "tools_node":
                    n      = len(node_out.get("raw_findings", []))
                    detail = f"{n} results found"
                elif node_name == "grader_node":
                    sc     = node_out.get("quality_score",    0)
                    rd     = node_out.get("routing_decision", "write")
                    detail = f"Score: {sc} → {rd}"
                elif node_name == "analyst_node":
                    ao     = node_out.get("analyst_output")
                    detail = f"Risk: {ao.risk_level}" if ao else ""
                elif node_name == "writer_node":
                    fr     = node_out.get("final_report")
                    detail = f"Confidence: {fr.confidence}%" if fr else ""

                tracker.done(node_name, detail)

                # Update progress bar
                pct, msg = node_progress.get(node_name, (50, "Working..."))
                progress.progress(pct, text=msg)
                status_box.info(msg)

                # Accumulate state
                if final_result is None:
                    final_result = dict(initial)
                final_result.update(node_out)

            elapsed = round(time.time() - start_t, 1)

            # Get complete state via invoke
            complete_result = dossier_graph.invoke(initial)
            complete_result["loop_count"] = final_result.get(
                "loop_count", 0
            )

            progress.progress(100, text="✅ Research complete!")
            status_box.success(
                f"✅ Dossier complete in **{elapsed}s**"
            )

            # ── Show results ──────────────────────────
            display_report(complete_result, elapsed)

        except Exception as e:
            progress.empty()
            status_box.error(f"❌ Pipeline failed: {str(e)}")
            st.markdown("""
            **Troubleshooting:**
            - Check `GROQ_API_KEY` in your `.env` file
            - Check `TAVILY_API_KEY` in your `.env` file
            - Run from project root directory
            - Check terminal for detailed error logs
            """)

    elif run_btn and not subject:
        st.warning("⚠️ Please enter a subject to research.")


if __name__ == "__main__":
    main()