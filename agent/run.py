import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.graph import agent_graph
from agent.state import AgentState


def run_agent(subject: str) -> dict:
#Vibe coded the CLI ui part lol
    print(f"""
╔══════════════════════════════════════════════╗
║             MINI DOSSIER AGENT               ║
╚══════════════════════════════════════════════╝
Subject: {subject}
""")

    start = time.time()
    # Initial state, sob faka
    initial_state: AgentState = {
        "subject"          : subject,
        "subject_type"     : "",
        "research_plan"    : [],
        "search_queries"   : [],
        "raw_findings"     : [],
        "errors"           : [],
        "search_count"     : 0,
        "quality_score"    : 0,
        "routing_decision" : "",
        "enriched_data"    : "",
        "final_report"     : None,
        "status"           : ""
    }

    result  = agent_graph.invoke(initial_state)
    elapsed = round(time.time() - start, 1)
    return result, elapsed


def display_report(result: dict, elapsed: float):
    """Pretty prints the final DossierReport."""

    report = result.get("final_report")
    status = result.get("status", "unknown")
    errors = result.get("errors", [])

    if not report:
        print("No report generated.")
        return

    risk_icons = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}
    risk_icon  = risk_icons.get(report.risk_level, "⚪")

    print(f"""
{'═'*55}
              INTELLIGENCE DOSSIER
{'═'*55}

📋 SUBJECT      : {report.subject}
🏷️  TYPE         : {report.subject_type.upper()}
{risk_icon} RISK LEVEL   : {report.risk_level}
📊 CONFIDENCE   : {report.confidence}/100
🔗 SOURCES USED : {report.sources_used}
⏱️  TIME TAKEN   : {elapsed}s
✅ STATUS        : {status.upper()}

{'─'*55}
OVERVIEW:
{report.overview}

{'─'*55}
KEY FACTS:""")

    for i, fact in enumerate(report.key_facts, 1):
        print(f"  {i}. {fact}")

    print(f"""
{'─'*55}
RISK ASSESSMENT:
{risk_icon} Level  : {report.risk_level}
   Reason : {report.risk_reason}

{'─'*55}
TAGS: {' | '.join([f'#{t}' for t in report.tags])}
{'═'*55}""")

    # Show graph stats
    print(f"\n📈 GRAPH STATS:")
    print(f"   Total searches : {result.get('search_count', 0)}")
    print(f"   Queries run    : {len(result.get('search_queries', []))}")
    print(f"   Findings items : {len(result.get('raw_findings', []))}")
    print(f"   Quality score  : {result.get('quality_score', 0)}/100")
    print(f"   Routing took   : {result.get('routing_decision', 'N/A')}")

    if errors:
        print(f"\n⚠️  ERRORS ENCOUNTERED: {len(errors)}")
        for e in errors[:3]:
            print(f"   • {e}")


if __name__ == "__main__":
    # Get subject from CLI or use default
    subject = (
        sys.argv[1]
        if len(sys.argv) > 1
        else "Mistral AI"
    )

    result, elapsed = run_agent(subject)
    display_report(result, elapsed)