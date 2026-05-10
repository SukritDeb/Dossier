# app.py
# ══════════════════════════════════════════════════════
# DOSSIER-AGENT — STREAMLIT WEB APPLICATION
#
# Run with: streamlit run app.py
#
# All imports use "agent" package (not "dossier_agent")
# Graph variable is "agent_graph" (not "dossier_graph")
# ══════════════════════════════════════════════════════

import sys
import os
import json
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

# ── ALL IMPORTS USE "agent" PACKAGE ──────────────────
from agent.graph  import agent_graph
from agent.state  import AgentState
from agent.config import RISK_ICONS, VERDICT_ICONS, OUTPUTS_DIR


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
    font-size      : 13px;
    font-weight    : bold;
    color          : #8b949e;
    text-transform : uppercase;
    letter-spacing : 1px;
    margin         : 16px 0 8px 0;
    border-bottom  : 1px solid #21262d;
    padding-bottom : 4px;
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
    det  = (
        f"<br><small style='color:#8b949e'>{detail}</small>"
        if detail else ""
    )
    return (
        f"<div class='node-card node-{status}'>"
        f"{icon} <b>{label}</b>{det}"
        f"</div>"
    )


def risk_badge(level: str) -> str:
    icon = RISK_ICONS.get(level, "⚪")
    return f"<span class='risk-{level}'>{icon} {level}</span>"


def stat_card(value: str, label: str) -> str:
    return (
        f"<div class='stat-card'>"
        f"<div class='stat-value'>{value}</div>"
        f"<div class='stat-label'>{label}</div>"
        f"</div>"
    )


def load_history() -> list:
    """Load saved JSON dossiers from outputs/ folder."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    files = sorted(
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


def build_initial_state(subject: str) -> AgentState:
    """Returns a clean initial AgentState dict."""
    return {
        "subject"          : subject,
        "subject_type"     : "",
        "research_plan"    : [],
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

# Progress % and message shown when each node completes
NODE_PROGRESS = {
    "intake_node"   : (20,  "🧠 Intake done — planning research..."),
    "planner_node"  : (30,  "📋 Plan ready — selecting tools..."),
    "tools_node"    : (50,  "🔍 Searches complete — grading quality..."),
    "grader_node"   : (62,  "⚖️  Graded — routing decision made..."),
    "enricher_node" : (72,  "🔬 Enrichment complete..."),
    "analyst_node"  : (82,  "🧩 Analysis done — writing report..."),
    "writer_node"   : (93,  "✍️  Report written — saving..."),
    "saver_node"    : (100, "✅ Complete!")
}


class NodeTracker:
    """Updates Streamlit UI as each node executes."""

    def __init__(self, placeholder):
        self.placeholder = placeholder
        self.statuses    = {k: "waiting" for k in NODE_LABELS}
        self.details     = {k: ""        for k in NODE_LABELS}
        self._render()

    def _render(self):
        html = "<div style='padding:4px'>"
        for node_id, label in NODE_LABELS.items():
            html += node_card(label, self.statuses[node_id],
                              self.details[node_id])
        html += "</div>"
        self.placeholder.markdown(html, unsafe_allow_html=True)

    def start(self, node_id: str):
        if node_id in self.statuses:
            self.statuses[node_id] = "running"
            self.details[node_id]  = "Working..."
            self._render()

    def done(self, node_id: str, detail: str = ""):
        if node_id in self.statuses:
            self.statuses[node_id] = "done"
            self.details[node_id]  = detail
            self._render()

    def finish_all(self):
        for k in self.statuses:
            if self.statuses[k] == "running":
                self.statuses[k] = "done"
        self._render()


# ══════════════════════════════════════════════════════
# REPORT DISPLAY
# ══════════════════════════════════════════════════════

def display_report(result: dict, elapsed: float):
    """Renders the final DossierReport in a rich UI."""

    report = result.get("final_report")
    status = result.get("status", "unknown")

    if not report:
        st.error("❌ No report was generated.")
        return

    # ── Top metrics row ───────────────────────────────
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
            stat_card(str(result.get("search_count", 0)), "Searches"),
            unsafe_allow_html=True
        )
    with c5:
        st.markdown(
            stat_card(f"{elapsed}s", "Time"),
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Subject header ────────────────────────────────
    verdict_color = (
        "#3fb950" if status == "complete" else "#d29922"
    )
    st.markdown(f"""
    <h2 style='color:#e6edf3; margin-bottom:4px;'>
        {report.subject}
    </h2>
    <div style='color:#8b949e; font-size:14px; margin-bottom:12px;'>
        {report.subject_type.upper()}
        &nbsp;|&nbsp;
        {risk_badge(report.risk_level)}
        &nbsp;|&nbsp;
        <span style='color:{verdict_color}'>
            {VERDICT_ICONS.get(status, "📋")} {status.upper()}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Two column layout ─────────────────────────────
    left_col, right_col = st.columns([3, 2])

    # ── LEFT: Overview + Facts + Events ──────────────
    with left_col:

        st.markdown(
            "<div class='section-header'>📋 Overview</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div style='color:#c9d1d9; line-height:1.7'>"
            f"{report.overview}</div>",
            unsafe_allow_html=True
        )

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

        # Notable events — only show if field exists
        notable = getattr(report, "notable_events", [])
        if notable:
            st.markdown(
                "<div class='section-header'>📅 Notable Events</div>",
                unsafe_allow_html=True
            )
            for event in notable:
                st.markdown(f"• {event}")

    # ── RIGHT: Risk + Relationships + Tags + Stats ────
    with right_col:

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

        # Risk factors — only show if field exists
        risk_factors = getattr(report, "risk_factors", [])
        if risk_factors:
            st.markdown("<br>**Risk Factors:**")
            for rf in risk_factors:
                st.markdown(
                    f"<div style='color:#f85149; font-size:13px;'>"
                    f"⚠️ {rf}</div>",
                    unsafe_allow_html=True
                )

        # Key relationships — only show if field exists
        key_relationships = getattr(report, "key_relationships", [])
        if key_relationships:
            st.markdown(
                "<div class='section-header'>🔗 Key Relationships</div>",
                unsafe_allow_html=True
            )
            for rel in key_relationships:
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
        er = len(result.get("errors",       []))

        st.markdown(f"""
        <div style='font-size:13px; color:#8b949e; line-height:2'>
          🔀 Final routing &nbsp;:
          <span class='route-badge'>{rd}</span><br>
          📊 Quality score &nbsp;:
          <b style='color:#e6edf3'>{qs}/100</b><br>
          ⚠️  Errors caught &nbsp;:
          <b style='color:#e6edf3'>{er}</b><br>
          🔄 Search loops &nbsp;&nbsp;:
          <b style='color:#e6edf3'>{result.get("loop_count", 0)}</b>
        </div>
        """, unsafe_allow_html=True)

    # ── Download button ───────────────────────────────
    st.markdown("---")

    payload = {
        "timestamp"  : datetime.now().isoformat(),
        "subject"    : report.subject,
        "status"     : status,
        "report"     : report.model_dump(),
        "graph_stats": {
            "searches"     : result.get("search_count", 0),
            "quality_score": qs,
            "routing"      : rd
        }
    }

    dl_col, saved_col = st.columns([1, 3])
    with dl_col:
        st.download_button(
            label               = "💾 Download JSON Report",
            data                = json.dumps(payload, indent=2),
            file_name           = (
                f"dossier_{report.subject.replace(' ', '_')}.json"
            ),
            mime                = "application/json",
            use_container_width = True
        )
    with saved_col:
        if result.get("output_path"):
            st.success(f"✅ Auto-saved: `{result['output_path']}`")


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

        with st.expander("ℹ️ How it works"):
            st.markdown("""
**Pipeline nodes:**

1. **Intake** — classifies + plans research
2. **Planner** — picks tools + writes queries
3. **Tools** — runs web searches
4. **Grader** — scores quality → routes
5. **Enricher** — fills gaps *(if needed)*
6. **Analyst** — deep risk analysis
7. **Writer** — structured report
8. **Saver** — saves to JSON

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
            verdict = item.get("status",    "?")
            risk    = report.get("risk_level",  "?")
            conf    = report.get("confidence",  "?")

            risk_icon    = RISK_ICONS.get(risk,    "⚪")
            verdict_icon = VERDICT_ICONS.get(verdict, "📋")

            label = subject[:25] + ("..." if len(subject) > 25 else "")
            with st.expander(f"{risk_icon} {label}"):
                st.markdown(f"""
                <div class='history-item'>
                  <div style='color:#e6edf3; font-weight:bold;'>
                    {subject}
                  </div>
                  <div style='color:#8b949e; font-size:12px;
                              margin-top:4px;'>
                    {verdict_icon} {verdict.upper()} &nbsp;|&nbsp;
                    {risk_icon} {risk} &nbsp;|&nbsp;
                    📊 {conf}%
                  </div>
                  <div style='color:#6e7681; font-size:11px;
                              margin-top:2px;'>
                    🕐 {ts}
                  </div>
                </div>
                """, unsafe_allow_html=True)

                facts = report.get("key_facts", [])[:3]
                if facts:
                    st.markdown("**Top facts:**")
                    for f in facts:
                        preview = f[:80] + ("..." if len(f) > 80 else "")
                        st.markdown(
                            f"<div style='font-size:12px; color:#8b949e;'>"
                            f"• {preview}</div>",
                            unsafe_allow_html=True
                        )


# ══════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════

def main():

    render_sidebar()

    # ── Header ────────────────────────────────────────
    st.markdown("""
    <div style='text-align:center; padding:20px 0 10px 0;'>
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
    <hr style='border-color:#21262d; margin:10px 0 20px 0;'>
    """, unsafe_allow_html=True)

    # ── How it works ──────────────────────────────────
    with st.expander("💡 How it works — click to expand"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("""
            **🧠 Plan**
            Intake node classifies your subject and builds
            a tailored research plan.
            """)
        with c2:
            st.markdown("""
            **🔍 Search**
            5 specialized tools search different angles —
            news, risk, financials, deep research.
            """)
        with c3:
            st.markdown("""
            **⚖️ Grade & Route**
            Quality grader scores findings and dynamically
            routes to enrich or write.
            """)
        with c4:
            st.markdown("""
            **📋 Report**
            Analyst + Writer produce a validated dossier
            with full risk scoring.
            """)

    # ── Input ─────────────────────────────────────────
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
        ("👤 Sam Altman",     "Sam Altman"),
        ("🏢 Mistral AI",     "Mistral AI"),
        ("👤 Yann LeCun",     "Yann LeCun"),
        ("🏢 Perplexity AI",  "Perplexity AI"),
        ("👤 Demis Hassabis", "Demis Hassabis"),
    ]

    for col, (label, value) in zip(
        [ex1, ex2, ex3, ex4, ex5], examples
    ):
        with col:
            if st.button(label, use_container_width=True):
                subject = value
                run_btn = True

    # ── Run pipeline ──────────────────────────────────
    if run_btn and subject:

        st.markdown("---")

        track_col, status_col = st.columns([2, 3])

        with track_col:
            st.markdown("### ⚙️ Pipeline")
            node_placeholder = st.empty()
            tracker          = NodeTracker(node_placeholder)

        with status_col:
            st.markdown("### 📡 Live Status")
            progress   = st.progress(0, text="Initializing...")
            status_box = st.empty()
            status_box.info(
                f"🚀 Starting research on: **{subject}**"
            )

        try:
            start_t      = time.time()
            initial      = build_initial_state(subject)
            final_result = dict(initial)

            # ── Stream node by node ───────────────────
            for step in agent_graph.stream(initial):

                node_name = list(step.keys())[0]
                node_out  = step[node_name]

                # Start indicator
                tracker.start(node_name)

                # Build per-node detail string
                detail = ""
                if node_name == "intake_node":
                    t      = node_out.get("subject_type", "?")
                    c      = node_out.get("complexity",   "?")
                    detail = f"Type: {t} | {c}"

                elif node_name == "planner_node":
                    q      = node_out.get("search_queries", [])
                    detail = f"{len(q)} queries planned"

                elif node_name == "tools_node":
                    n      = len(node_out.get("raw_findings", []))
                    detail = f"{n} results found"

                elif node_name == "grader_node":
                    sc     = node_out.get("quality_score",    0)
                    rd     = node_out.get("routing_decision", "write")
                    detail = f"Score: {sc} → {rd}"

                elif node_name == "enricher_node":
                    detail = "Gap filled with deep search"

                elif node_name == "analyst_node":
                    ao     = node_out.get("analyst_output")
                    detail = f"Risk: {ao.risk_level}" if ao else ""

                elif node_name == "writer_node":
                    fr     = node_out.get("final_report")
                    detail = (
                        f"Confidence: {fr.confidence}%"
                        if fr else ""
                    )

                elif node_name == "saver_node":
                    op     = node_out.get("output_path", "")
                    detail = "Saved ✅" if op else "Save skipped"

                tracker.done(node_name, detail)

                # Update progress bar
                pct, msg = NODE_PROGRESS.get(
                    node_name, (50, "Working...")
                )
                progress.progress(pct, text=msg)
                status_box.info(msg)

                # Accumulate state
                final_result.update(node_out)

            elapsed = round(time.time() - start_t, 1)

            # ── Get complete final state via invoke ───
            # stream() gives per-node diffs only;
            # invoke() gives the full merged final state
            complete = agent_graph.invoke(initial)
            complete["loop_count"] = final_result.get(
                "loop_count", 0
            )

            progress.progress(100, text="✅ Research complete!")
            status_box.success(
                f"✅ Dossier complete in **{elapsed}s**"
            )

            display_report(complete, elapsed)

        except Exception as e:
            progress.empty()
            status_box.error(f"❌ Pipeline failed: {str(e)}")
            st.markdown("""
            **Troubleshooting:**
            - Check `GROQ_API_KEY` in your `.env` file
            - Check `TAVILY_API_KEY` in your `.env` file
            - Run from the project root directory
            - Check terminal for detailed error logs
            """)

    elif run_btn and not subject:
        st.warning("⚠️ Please enter a subject to research.")


if __name__ == "__main__":
    main()