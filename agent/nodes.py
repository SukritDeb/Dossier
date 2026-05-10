import os
import json
from typing import Literal
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
from langchain_core.messages import SystemMessage          # ← KEY FIX

from agent.state import AgentState, DossierReport
from agent.tools import (
    search_general,
    search_news,
    search_deep,
    search_risk_signals,
    ALL_TOOLS
)

load_dotenv()

_llm = ChatGroq(
    api_key     = os.getenv("GROQ_API_KEY"),
    model       = "llama-3.3-70b-versatile",
    temperature = 0.1
)

_llm_writer = ChatGroq(
    api_key     = os.getenv("GROQ_API_KEY"),
    model       = "llama-3.3-70b-versatile",
    temperature = 0.6
)


# SAFE CHAIN CALL 
def _safe(chain, inputs: dict, fallback):
    try:
        return chain.invoke(inputs)
    except Exception as e:
        print(f"Chain error: {e}")
        return fallback

# NODE 1: INTAKE
# Classifies subject and builds a research plan

def intake_node(state: AgentState) -> dict:
    print(f"\n{'═'*50}")
    print(f"INTAKE NODE")

    # Expand ambiguous single-word subjects
    # "Elon" to "Elon Musk", "Tesla" stays "Tesla"
    # Prevents searching for university instead of person
    subject = state["subject"]

    if len(subject.strip().split()) == 1:
        try:
            clarify = _llm.invoke(
                f"What is the single most famous real-world "
                f"person or company named '{subject}'? "
                f"Reply with only the full proper name, "
                f"nothing else. No punctuation. No explanation."
            )
            expanded = clarify.content.strip().strip('"').strip("'")

            # Only use expansion if it's longer and looks valid
            if (
                expanded
                and len(expanded) > len(subject)
                and len(expanded) < 60
                and "\n" not in expanded
            ):
                print(f"Expanded '{subject}' → '{expanded}'")
                subject = expanded
            else:
                print(f"   Subject: '{subject}' (no expansion needed)")

        except Exception as e:
            print(f"Name expansion failed: {e}")
            print(f"Subject: '{subject}' (using original)")

    else:
        print(f"Subject: '{subject}'")

    system_message = SystemMessage(content=(
        "You are an intelligence analyst intake specialist.\n"
        "Analyze the subject and create a research plan.\n\n"
        "Return ONLY valid JSON in this format:\n"
        "{\n"
        '  "subject_type": "person" or "company" or "unknown",\n'
        '  "research_plan": [\n'
        '    "angle 1 to research",\n'
        '    "angle 2 to research",\n'
        '    "angle 3 to research"\n'
        "  ]\n"
        "}\n\n"
        "Research angles should be SPECIFIC:\n"
        "- For a person  : career history, major achievements,\n"
        "                  controversies, net worth, personal life\n"
        "- For a company : products/services, revenue and funding,\n"
        "                  leadership team, competitors, recent news"
    ))

    prompt = ChatPromptTemplate.from_messages([
        system_message,
        ("human", "Create intake analysis for: {subject}")
    ])

    try:
        chain  = prompt | _llm | JsonOutputParser()
        result = chain.invoke({"subject": subject})

        s_type = result.get("subject_type", "unknown")
        plan   = result.get("research_plan", [subject])

        print(f"   Type  : {s_type}")
        print(f"   Plan  : {plan}")

        return {
            "subject"         : subject,   
            "subject_type"    : s_type,
            "research_plan"   : plan,
            "search_count"    : 0,
            "status"          : "in_progress"
        }

    except Exception as e:
        print(f"Intake error: {e}")
        return {
            "subject"         : subject,
            "subject_type"    : "unknown",
            "research_plan"   : [f"general information about {subject}"],
            "search_count"    : 0,
            "errors"          : [f"intake_node: {str(e)}"],
            "status"          : "in_progress"
        }

# NODE 2: PLANNER
# Decides WHICH tools to call and with WHAT queries

def planner_node(state: AgentState) -> dict:
    print(f"\n PLANNER NODE")
    print(f"Loop #{state.get('loop_count', 0) + 1}")

    # Build gaps context string
    gaps_context = ""
    if state.get("quality_gaps"):
        gaps_context = (
            "\n\nKNOWN GAPS TO FILL:\n" +
            "\n".join(f"  - {g}" for g in state["quality_gaps"])
        )

    # SystemMessage object — bypasses LangChain template
    # parsing so JSON braces don't cause crashes
    system_message = SystemMessage(content=(
        "You are a research planner for an intelligence dossier.\n\n"
        "Available tools:\n"
        "  search_general     -> broad background facts\n"
        "  search_news        -> recent news and events\n"
        "  search_deep        -> detailed specific research\n"
        "  search_risk        -> controversies and risk signals\n"
        "  search_financials  -> financial data and funding\n\n"
        "Return ONLY valid JSON in this EXACT format:\n"
        "{\n"
        '  "tool_calls": [\n'
        '    {"tool": "tool_name", "query": "specific query"},\n'
        '    {"tool": "tool_name", "query": "specific query"},\n'
        '    {"tool": "tool_name", "query": "specific query"}\n'
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Always include search_risk (pass subject name as query)\n"
        "- Always include search_news\n"
        "- Max 4 tool calls total\n"
        "- Make queries SPECIFIC and TARGETED\n"
        "- If gaps exist, prioritize filling them"
        + gaps_context
    ))

    prompt = ChatPromptTemplate.from_messages([
        system_message,
        (
            "human",
            "Subject: {subject} ({subject_type})\n"
            "Complexity: {complexity}\n"
            "Research angles:\n{angles}\n\n"
            "Plan the tool calls now."
        )
    ])

    chain = prompt | _llm | JsonOutputParser()

    result = _safe(
        chain,
        {
            "subject"     : state["subject"],
            "subject_type": state.get("subject_type", "unknown"),
            "complexity"  : state.get("complexity",   "moderate"),
            "angles"      : "\n".join([
                f"  - {a}"
                for a in state.get("research_plan", [state["subject"]])
            ])
        },
        {
            "tool_calls": [
                {"tool": "search_general",
                 "query": state["subject"]},
                {"tool": "search_news",
                 "query": f"{state['subject']} latest news 2025"},
                {"tool": "search_risk",
                 "query": state["subject"]}
            ]
        }
    )

    tool_calls = result.get("tool_calls", [])

    # Guard: fallback if result is malformed
    if not isinstance(tool_calls, list) or not tool_calls:
        tool_calls = [
            {"tool": "search_general", "query": state["subject"]},
            {"tool": "search_risk",    "query": state["subject"]}
        ]

    queries = [tc.get("query", state["subject"]) for tc in tool_calls]

    print(f"   Planned {len(tool_calls)} tool calls:")
    for tc in tool_calls:
        print(f"   → {tc.get('tool','?')}('{tc.get('query','')[:45]}')")

    return {
        "search_queries": queries,
        "_tool_plan"    : tool_calls
    }

# NODE 3: TOOLS
# Executes the tool calls decided by planner

TOOL_MAP = {
    "search_general"     : search_general,
    "search_news"        : search_news,
    "search_deep"        : search_deep,
    "search_risk"        : search_risk_signals,
    "search_risk_signals": search_risk_signals,
    "search_financials"  : search_general,   # fallback to general
}


# Which tools take "subject" vs "query" 
SUBJECT_TOOLS = {"search_risk_signals", "search_risk"}

def tools_node(state: AgentState) -> dict:
    print(f"\n📍 TOOLS NODE")

    tool_plan = state.get("_tool_plan", [])

    if not tool_plan:
        tool_plan = [
            {"tool": "search_general", "query": state["subject"]},
            {"tool": "search_risk",    "query": state["subject"]}
        ]

    new_findings = []
    new_errors   = []

    for call in tool_plan:
        tool_name = call.get("tool", "search_general")
        query     = call.get("query", state["subject"])
        tool_fn   = TOOL_MAP.get(tool_name, search_general)

        try:
            print(f"{tool_name}('{query[:50]}')")
            # search_risk_signals uses "subject" not "query"
            if tool_name in SUBJECT_TOOLS:
                result = tool_fn.invoke({"subject": query})
            else:
                result = tool_fn.invoke({"query": query})

            tagged = f"[SOURCE: {tool_name}]\n{result}"
            new_findings.append(tagged)
            print(f"{len(result)} chars returned")

        except Exception as e:
            new_errors.append(f"tools_node/{tool_name}: {str(e)}")
            print(f"Failed: {e}")

    total = state.get("search_count", 0) + len(tool_plan)
    print(f"\n   Total findings: {len(new_findings)} tool results")

    return {
        "raw_findings": new_findings,
        "errors"      : new_errors,
        "search_count": total
    }

# NODE 4: GRADER
# Evaluates research quality → routing decision

def grader_node(state: AgentState) -> dict:
    print(f"\n GRADER NODE")

    # Safety valve — force write after enough searches
    if state.get("search_count", 0) >= 6:
        print(f"Max searches reached → forcing write")
        return {
            "quality_score"   : 65,
            "routing_decision": "write"
        }
    findings_count = len(state.get("raw_findings", []))
    if findings_count == 0:
        print(f"No findings → re_search")
        return {
            "quality_score"   : 0,
            "routing_decision": "re_search"
        }

    sample = "\n---\n".join(
        state["raw_findings"][:3]
    )[:1500]

    # SystemMessage object avoids crash on JSON braces
    system_message = SystemMessage(content=(
        "You grade research quality for intelligence dossiers.\n\n"
        "Return ONLY valid JSON in this format:\n"
        "{\n"
        '  "score": <integer 0-100>,\n'
        '  "decision": "re_search" or "enrich" or "write",\n'
        '  "reason": "one sentence"\n'
        "}\n\n"
        "Scoring guide:\n"
        "  85-100 -> write      (rich, detailed, multi-source)\n"
        "  60-84  -> enrich     (decent but missing some depth)\n"
        "  0-59   -> re_search  (too thin or vague)"
    ))

    prompt = ChatPromptTemplate.from_messages([
        system_message,
        (
            "human",
            "Subject: {subject}\n"
            "Findings count: {count}\n"
            "Sample findings:\n{sample}\n\n"
            "Grade this research."
        )
    ])

    chain  = prompt | _llm | JsonOutputParser()
    result = _safe(chain, {
        "subject": state["subject"],
        "count"  : findings_count,
        "sample" : sample
    }, {"score": 60, "decision": "write", "reason": "fallback"})

    score    = int(result.get("score",    60))
    decision = result.get("decision", "write")
    reason   = result.get("reason",   "")

    print(f"   Score    : {score}/100")
    print(f"   Decision : {decision}")
    print(f"   Reason   : {reason}")

    return {
        "quality_score"   : score,
        "routing_decision": decision
    }

# ROUTER FUNCTION (not a node — called by LangGraph)

def grade_router(
    state: AgentState
) -> Literal["planner_node", "enricher_node", "writer_node"]:
    """
    Reads routing_decision and routes to:
    re_search → planner_node  (loop back, search again)
    enrich    → enricher_node (targeted gap filling)
    write     → writer_node   (enough info, write report)
    """
    decision = state.get("routing_decision", "write")

    routes = {
        "re_search": "planner_node",
        "enrich"   : "enricher_node",
        "write"    : "writer_node"
    }

    destination = routes.get(decision, "writer_node")
    print(f"\nROUTING: '{decision}' → '{destination}'")
    return destination

# NODE 5: ENRICHER
# Runs one targeted deep search to fill a gap

def enricher_node(state: AgentState) -> dict:
    print(f"\n ENRICHER NODE")

    existing = "\n".join(state.get("raw_findings", []))[:1000]

    # SystemMessage object — JSON braces are literal here
    system_message = SystemMessage(content=(
        "You identify gaps in research findings.\n"
        "Return ONLY valid JSON in this format:\n"
        "{\n"
        '  "missing_angle": "what is most missing",\n'
        '  "deep_query": "specific search query to fill the gap"\n'
        "}"
    ))

    prompt = ChatPromptTemplate.from_messages([
        system_message,
        (
            "human",
            "Subject: {subject}\n"
            "Existing findings:\n{existing}\n\n"
            "What is missing and what should we search for?"
        )
    ])

    try:
        chain  = prompt | _llm | JsonOutputParser()
        result = chain.invoke({
            "subject" : state["subject"],
            "existing": existing
        })

        deep_query = result.get(
            "deep_query",
            f"{state['subject']} detailed background"
        )
        missing    = result.get("missing_angle", "additional context")

        print(f"   Missing: {missing}")
        print(f"   Query  : '{deep_query}'")

        deep_result = search_deep.invoke({"query": deep_query})
        enriched    = f"[ENRICHED - {missing}]\n{deep_result}"

        print(f"Enrichment complete ({len(deep_result)} chars)")

        return {
            "raw_findings"  : [enriched],
            "search_queries": [deep_query],
            "search_count"  : state.get("search_count", 0) + 1,
            "enriched_data" : enriched
        }

    except Exception as e:
        print(f"Enricher error: {e}")
        return {
            "errors"       : [f"enricher_node: {str(e)}"],
            "enriched_data": ""
        }

# NODE 6: WRITER
# Produces final structured DossierReport

def writer_node(state: AgentState) -> dict:
    print(f"\n WRITER NODE")
    print(f"Writing from {len(state.get('raw_findings', []))} findings...")

    all_findings = "\n\n".join(state.get("raw_findings", []))[:4000]

    # SystemMessage object — the JSON schema has many { }
    # that would crash LangChain's template parser
    system_message = SystemMessage(content=(
        "You write structured intelligence dossiers.\n"
        "Based on research findings, produce a JSON dossier.\n\n"
        "Return ONLY valid JSON matching this EXACT structure:\n"
        "{\n"
        '  "subject": "full name",\n'
        '  "subject_type": "person or company",\n'
        '  "overview": "2-3 sentence overview",\n'
        '  "key_facts": ["fact1", "fact2", "fact3", "fact4", "fact5"],\n'
        '  "risk_level": "LOW or MEDIUM or HIGH",\n'
        '  "risk_reason": "one sentence explaining risk level",\n'
        '  "tags": ["tag1", "tag2", "tag3"],\n'
        '  "confidence": <integer 0-100>,\n'
        '  "sources_used": <integer>\n'
        "}\n\n"
        "Rules:\n"
        "- key_facts must have EXACTLY 5 items\n"
        "- confidence = how complete and consistent the research is\n"
        "- sources_used = count of [SOURCE:...] blocks in findings"
    ))

    prompt = ChatPromptTemplate.from_messages([
        system_message,
        (
            "human",
            "Subject: {subject} ({subject_type})\n\n"
            "Research findings:\n{findings}\n\n"
            "Write the dossier JSON."
        )
    ])

    try:
        chain  = prompt | _llm_writer | JsonOutputParser()
        raw    = chain.invoke({
            "subject"     : state["subject"],
            "subject_type": state.get("subject_type", "unknown"),
            "findings"    : all_findings
        })

        # Override sources_used with actual count
        raw["sources_used"] = len(state.get("raw_findings", []))

        # Validate with Pydantic
        report = DossierReport(**raw)

        print(f"Report validated — confidence {report.confidence}/100")

        return {
            "final_report": report,
            "status"      : "complete"
        }

    except Exception as e:
        print(f"Writer error: {e}")

        # Fallback minimal report
        fallback = DossierReport(
            subject      = state["subject"],
            subject_type = state.get("subject_type", "unknown"),
            overview     = (
                f"Research completed for {state['subject']} "
                f"with limited structured data."
            ),
            key_facts    = [
                f"Subject: {state['subject']}",
                "Full structured data unavailable",
                "Research was attempted",
                "Partial information gathered",
                "Manual review recommended"
            ],
            risk_level   = "MEDIUM",
            risk_reason  = "Insufficient data to assess risk accurately",
            tags         = [state["subject"], "research", "dossier"],
            confidence   = 20,
            sources_used = len(state.get("raw_findings", []))
        )

        return {
            "final_report": fallback,
            "status"      : "partial",
            "errors"      : [f"writer_node: {str(e)}"]
        }