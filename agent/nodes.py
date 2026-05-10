import os
import json
from typing import Literal
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from agent.state  import AgentState, DossierReport
from agent.tools  import (
    search_general,
    search_news,
    search_deep,
    search_risk_signals,
    ALL_TOOLS
)

load_dotenv()

llm = ChatGroq(
    api_key     = os.getenv("GROQ_API_KEY"),
    model       = "llama-3.3-70b-versatile",
    temperature = 0.1
)

llm_creative = ChatGroq(
    api_key     = os.getenv("GROQ_API_KEY"),
    model       = "llama-3.3-70b-versatile",
    temperature = 0.6  
)

# NODE 1: INTAKE
# Classifies subject and builds a research plan

def intake_node(state: AgentState) -> dict:
    print(f"\n{'═'*50}")
    print(f"INTAKE NODE")
    print(f"Subject: '{state['subject']}'")

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an intelligence analyst intake specialist.
Analyze the subject and create a research plan.

Return ONLY valid JSON:
{{
  "subject_type"  : "person" or "company" or "unknown",
  "research_plan" : [
    "angle 1 to research",
    "angle 2 to research",
    "angle 3 to research"
  ]
}}

Research angles should be SPECIFIC:
- For a person: career, achievements, controversies, net worth
- For a company: products, revenue, leadership, competitors, news"""
        ),
        ("human", "Create intake analysis for: {subject}")
    ])

    try:
        chain  = prompt | llm | JsonOutputParser()
        result = chain.invoke({"subject": state["subject"]})

        s_type = result.get("subject_type", "unknown")
        plan   = result.get("research_plan", [state["subject"]])

        print(f"Type: {s_type}")
        print(f"Plan: {plan}")

        return {
            "subject_type"    : s_type,
            "research_plan"   : plan,
            "search_count"    : 0,
            "status"          : "in_progress"
        }

    except Exception as e:
        print(f"Intake error: {e}")
        return {
            "subject_type"    : "unknown",
            "research_plan"   : [f"general information about {state['subject']}"],
            "search_count"    : 0,
            "errors"          : [f"intake_node: {str(e)}"],
            "status"          : "in_progress"
        }

# NODE 2: PLANNER
# Decides which tools to call and with what queries

def planner_node(state: AgentState) -> dict:
    print(f"\n PLANNER NODE")

    # tool descriptions for the LLM
    tool_descriptions = """
        Available tools:
        - search_general     : overview and background facts
        - search_news        : recent news and events
        - search_deep        : detailed/technical deep research
        - search_risk_signals: controversies, scandals, legal issues
"""

    plan_text = "\n".join([
        f"  {i+1}. {p}"
        for i, p in enumerate(state.get("research_plan", []))
    ])

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            f"""You are a research planner.
Given a research plan, decide which tools to use.
{tool_descriptions}

Return ONLY valid JSON:
{{
  "tool_calls": [
    {{"tool": "search_general",      "query": "specific query here"}},
    {{"tool": "search_news",         "query": "specific query here"}},
    {{"tool": "search_risk_signals", "query": "subject name only"}}
  ]
}}

Always include search_risk_signals.
Max 4 tool calls total. Make queries SPECIFIC."""
        ),
        (
            "human",
            "Subject: {subject} ({subject_type})\n\n"
            "Research plan:\n{plan}\n\n"
            "Decide which tools to call."
        )
    ])

    try:
        chain  = prompt | llm | JsonOutputParser()
        result = chain.invoke({
            "subject"     : state["subject"],
            "subject_type": state.get("subject_type", "unknown"),
            "plan"        : plan_text
        })

        tool_calls = result.get("tool_calls", [])
        queries    = [tc["query"] for tc in tool_calls]

        print(f"Planned {len(tool_calls)} tool calls:")
        for tc in tool_calls:
            print(f"{tc['tool']}('{tc['query'][:50]}')")

        return {
            "search_queries": queries,
            "_tool_plan"    : tool_calls    # temp field for tools_node
        }

    except Exception as e:
        print(f"Planner error: {e}")
        # fallback plan
        fallback_queries = [
            f"{state['subject']} overview",
            f"{state['subject']} news 2025"
        ]
        return {
            "search_queries": fallback_queries,
            "errors": [f"planner_node: {str(e)}"]
        }

# NODE 3: TOOLS
# Actually executes the tool calls from planner

TOOL_MAP = {
    "search_general"     : search_general,
    "search_news"        : search_news,
    "search_deep"        : search_deep,
    "search_risk_signals": search_risk_signals
}

def tools_node(state: AgentState) -> dict:
    print(f"\n TOOLS NODE")
    # Get tool plan — if not set, fall back to queries
    tool_plan = state.get("_tool_plan", [])
    if not tool_plan:
        # Fallback: use queries with search_general
        tool_plan = [
            {"tool": "search_general", "query": q}
            for q in state.get("search_queries", [])[-2:]
        ]

    new_findings = []
    new_errors   = []

    for call in tool_plan:
        tool_name = call.get("tool", "search_general")
        query     = call.get("query", state["subject"])
        tool_fn   = TOOL_MAP.get(tool_name, search_general)
        try:
            print(f"{tool_name}('{query[:50]}')")
            result = tool_fn.invoke({"query": query})
            # Tag each finding with its source tool
            tagged = f"[SOURCE: {tool_name}]\n{result}"
            new_findings.append(tagged)
            print(f"{len(result)} chars returned")

        except Exception as e:
            new_errors.append(f"tools_node/{tool_name}: {str(e)}")
            print(f"Failed: {e}")

    print(f"\n   Total findings: {len(new_findings)} tool results")

    return {
        "raw_findings": new_findings,      
        "errors": new_errors,       
        "search_count": state.get("search_count", 0) + len(tool_plan)
    }

# NODE 4: GRADER
# Evaluates research quality → routing decision

def grader_node(state: AgentState) -> dict:
    print(f"\n GRADER NODE")
    # Safety valve
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
    # Sample findings for evaluation
    sample = "\n---\n".join(
        state["raw_findings"][:3]
    )[:1500]

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You grade research quality for intelligence dossiers.

Return ONLY valid JSON:
{{
  "score"    : <integer 0-100>,
  "decision" : "re_search" or "enrich" or "write",
  "reason"   : "one sentence"
}}

Scoring guide:
  85-100 → write      (rich, detailed, multi-source)
  60-84  → enrich     (decent but missing some depth)
  0-59   → re_search  (too thin or vague)"""
        ),
        (
            "human",
            "Subject: {subject}\n"
            "Findings count: {count}\n"
            "Sample findings:\n{sample}\n\n"
            "Grade this research."
        )
    ])

    try:
        chain  = prompt | llm | JsonOutputParser()
        result = chain.invoke({
            "subject": state["subject"],
            "count"  : findings_count,
            "sample" : sample
        })

        score    = int(result.get("score",    60))
        decision = result.get("decision", "write")
        reason   = result.get("reason",   "")

        print(f"Score: {score}/100")
        print(f"Decision: {decision}")
        print(f"Reason: {reason}")

        return {
            "quality_score": score,
            "routing_decision": decision
        }

    except Exception as e:
        print(f"Grader error: {e}")
        return {
            "quality_score"   : 60,
            "routing_decision": "write",
            "errors"          : [f"grader_node: {str(e)}"]
        }

# ROUTER FUNCTION (not a node — called by LangGraph)

def grade_router(
    state: AgentState
) -> Literal["planner_node", "enricher_node", "writer_node"]:
    """
    Reads routing_decision from grader and routes:
    re_search - planner_node  (start search loop again)
    enrich    - enricher_node (add specific depth)
    write     - writer_node   (we have enough, write it)
    """
    decision = state.get("routing_decision", "write")

    routes = {
        "re_search": "planner_node",
        "enrich"   : "enricher_node",
        "write"    : "writer_node"
    }

    destination = routes.get(decision, "writer_node")
    print(f"\n   🔀 ROUTING: '{decision}' → '{destination}'")
    return destination

# NODE 5: ENRICHER
# Called when we have decent but not great research
# Runs one targeted deep search based on gaps

def enricher_node(state: AgentState) -> dict:
    print(f"\n📍 ENRICHER NODE")
    # Ask LLM what's missing
    existing = "\n".join(state.get("raw_findings", []))[:1000]
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You identify gaps in research findings.
Return ONLY valid JSON:
{{
  "missing_angle": "what is most missing",
  "deep_query"   : "specific search query to fill the gap"
}}"""
        ),
        (
            "human",
            "Subject: {subject}\n"
            "Existing findings:\n{existing}\n\n"
            "What is missing and what should we search for?"
        )
    ])

    try:
        chain  = prompt | llm | JsonOutputParser()
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

        # Run the deep search
        deep_result = search_deep.invoke({"query": deep_query})
        enriched    = f"[ENRICHED - {missing}]\n{deep_result}"

        print(f"Enrichment complete ({len(deep_result)} chars)")

        return {
            "raw_findings"  : [enriched],       
            "search_queries": [deep_query],   
            "enriched_data" : enriched,
            "search_count"  : state.get("search_count", 0) + 1
        }

    except Exception as e:
        print(f"Enricher error: {e}")
        return {
            "errors": [f"enricher_node: {str(e)}"],
            "enriched_data": ""
        }

# NODE 6: WRITER
# Produces final structured DossierReport

def writer_node(state: AgentState) -> dict:
    print(f"\n WRITER NODE")
    print(f"   Writing from {len(state.get('raw_findings',[]))} findings...")
    all_findings = "\n\n".join(state.get("raw_findings", []))[:4000]

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You write structured intelligence dossiers.
Based on research findings, produce a JSON dossier.

Return ONLY valid JSON matching this EXACT structure:
{{
  "subject"      : "full name",
  "subject_type" : "person or company",
  "overview"     : "2-3 sentence overview",
  "key_facts"    : ["fact1", "fact2", "fact3", "fact4", "fact5"],
  "risk_level"   : "LOW or MEDIUM or HIGH",
  "risk_reason"  : "one sentence explaining risk level",
  "tags"         : ["tag1", "tag2", "tag3"],
  "confidence"   : <integer 0-100>,
  "sources_used" : <integer>
}}

Base confidence on how complete and consistent the research is.
Base sources_used on number of source blocks in findings."""
        ),
        (
            "human",
            "Subject: {subject} ({subject_type})\n\n"
            "Research findings:\n{findings}\n\n"
            "Write the dossier JSON."
        )
    ])

    try:
        chain  = prompt | llm | JsonOutputParser()
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
            overview     = f"Research completed for {state['subject']} with limited data.",
            key_facts    = ["Insufficient data for detailed facts"],
            risk_level   = "MEDIUM",
            risk_reason  = "Insufficient data to assess risk accurately",
            tags         = [state["subject"]],
            confidence   = 20,
            sources_used = len(state.get("raw_findings", []))
        )
        return {
            "final_report": fallback,
            "status"      : "partial",
            "errors"      : [f"writer_node: {str(e)}"]
        }