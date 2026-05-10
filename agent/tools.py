# lesson6/tools.py
# ══════════════════════════════════════════════════════
# ALL CUSTOM TOOLS — FIXED VERSION
#
# Fix 1: Updated from deprecated TavilySearchResults
#         to new langchain-tavily TavilySearch
# Fix 2: search_risk_signals now accepts BOTH
#         "subject" and "query" parameters so it
#         works whether called directly or via tools_node
#
# Install updated package first:
#   pip install -U langchain-tavily
# ══════════════════════════════════════════════════════

import os
from dotenv import load_dotenv
from langchain_core.tools import tool

# ── NEW IMPORT — replaces deprecated TavilySearchResults
try:
    from langchain_tavily import TavilySearch
    TAVILY_NEW = True
except ImportError:
    # Fallback to old package if new one not installed yet
    from langchain_community.tools.tavily_search import TavilySearchResults
    TAVILY_NEW = False
    print("⚠️  Using deprecated TavilySearchResults.")
    print("   Run: pip install -U langchain-tavily")

load_dotenv()


# ══════════════════════════════════════════════════════
# HELPER — creates Tavily client + runs search
# Handles both old and new package transparently
# ══════════════════════════════════════════════════════

def _tavily_search(
    query       : str,
    max_results : int = 4,
    search_depth: str = "basic",
    topic       : str = "general"
) -> list[dict]:
    """
    Runs a Tavily search and returns list of result dicts.
    Handles both old and new langchain-tavily packages.
    """
    if TAVILY_NEW:
        kwargs = dict(
            max_results  = max_results,
            search_depth = search_depth,
            api_key      = os.getenv("TAVILY_API_KEY")
        )
        if topic != "general":
            kwargs["topic"] = topic

        client  = TavilySearch(**kwargs)
        results = client.invoke({"query": query})

        # New package returns list of dicts directly
        if isinstance(results, list):
            return results

        # Sometimes returns dict with "results" key
        if isinstance(results, dict):
            return results.get("results", [])

        return []

    else:
        # Old package fallback
        kwargs = dict(
            api_key      = os.getenv("TAVILY_API_KEY"),
            max_results  = max_results,
            search_depth = search_depth
        )
        if topic != "general":
            kwargs["topic"] = topic

        client  = TavilySearchResults(**kwargs)
        results = client.invoke({"query": query})
        return results if isinstance(results, list) else []


def _format(results: list, tag: str) -> str:
    """Formats raw Tavily results into a tagged string."""
    if not results:
        return "No results found."

    out = ""
    for i, r in enumerate(results, 1):
        title   = r.get("title",   "No title")
        url     = r.get("url",     "")
        content = r.get("content", "")[:400]
        out += f"[{tag} {i}] {title}\n"
        out += f"    URL: {url}\n"
        out += f"    {content}\n\n"
    return out


# ══════════════════════════════════════════════════════
# TOOL 1: General Overview Search
# ══════════════════════════════════════════════════════

@tool
def search_general(query: str) -> str:
    """
    Search for general overview and background information.
    Use first to get a broad picture of the subject.
    Best for: Who is X, What is X, History of X,
    Overview of a company or person.

    Args:
        query: general search query string

    Returns:
        Formatted string of overview search results
    """
    results = _tavily_search(
        query        = query,
        max_results  = 4,
        search_depth = "basic"
    )
    return _format(results, "OVERVIEW")


# ══════════════════════════════════════════════════════
# TOOL 2: News Search
# ══════════════════════════════════════════════════════

@tool
def search_news(query: str) -> str:
    """
    Search for recent news, current events, and latest
    developments about the subject.
    Use for anything that happened in the past 1-2 years.
    Best for: recent changes, current status, latest news,
    announcements, updates.

    Args:
        query: news-focused search query string

    Returns:
        Formatted string of recent news results
    """
    results = _tavily_search(
        query        = query,
        max_results  = 4,
        search_depth = "advanced",
        topic        = "news"
    )
    return _format(results, "NEWS")


# ══════════════════════════════════════════════════════
# TOOL 3: Deep Research Search
# ══════════════════════════════════════════════════════

@tool
def search_deep(query: str) -> str:
    """
    Perform thorough deep research on a specific aspect
    of the subject. Use when you need detailed information.
    Best for: financial data, technical specifications,
    detailed biography, founding history, specific events.

    Args:
        query: specific and detailed search query string

    Returns:
        Detailed research results as formatted string
    """
    results = _tavily_search(
        query        = query,
        max_results  = 5,
        search_depth = "advanced"
    )
    return _format(results, "DEEP")


# ══════════════════════════════════════════════════════
# TOOL 4: Risk Signals Search
#
# FIX: Now accepts both "subject" and "query" parameters.
# tools_node passes "query", direct calls pass "subject".
# Both work correctly.
# ══════════════════════════════════════════════════════

@tool
def search_risk_signals(subject: str) -> str:
    """
    Search specifically for risk signals and negative
    information about the subject. ALWAYS call this tool
    for any dossier subject being researched.

    Finds: controversies, lawsuits, scandals, regulatory
    issues, fraud allegations, negative press, ethical
    concerns, safety violations, employee complaints.

    Args:
        subject: exact name of the person or company
                 to search risk signals for

    Returns:
        Risk signal findings as formatted string
    """
    queries = [
        f"{subject} controversy scandal criticism allegations",
        f"{subject} lawsuit legal regulatory investigation problem"
    ]

    all_results = []
    for q in queries:
        results      = _tavily_search(
            query       = q,
            max_results = 3
        )
        all_results.extend(results)

    return _format(all_results, "RISK") or "No significant risk signals found."


# ══════════════════════════════════════════════════════
# TOOL 5: Financial Search
# ══════════════════════════════════════════════════════

@tool
def search_financials(query: str) -> str:
    """
    Search for financial information, funding rounds,
    valuation, revenue figures, and investor details.
    Use for companies or high-profile individuals.
    Best for: net worth, funding history, revenue,
    investors, IPO details, acquisitions, valuation.

    Args:
        query: finance-focused search query string

    Returns:
        Financial information results as formatted string
    """
    results = _tavily_search(
        query        = query,
        max_results  = 4,
        search_depth = "advanced"
    )
    return _format(results, "FINANCIAL")


# ══════════════════════════════════════════════════════
# TOOL REGISTRY
# Used by tools_node to look up tool functions by name.
# All valid name aliases mapped to the correct function.
# ══════════════════════════════════════════════════════

TOOL_MAP = {
    # Primary names (what planner_node should output)
    "search_general"     : search_general,
    "search_news"        : search_news,
    "search_deep"        : search_deep,
    "search_risk"        : search_risk_signals,
    "search_financials"  : search_financials,

    # Aliases (for robustness — LLM sometimes varies names)
    "search_risk_signals": search_risk_signals,
    "search_overview"    : search_general,
    "search_background"  : search_general,
    "search_recent"      : search_news,
    "search_latest"      : search_news,
}

# ── Tools that take "subject" parameter ──────────────
# tools_node checks this set to pass the right param name
SUBJECT_TOOLS = {
    "search_risk",
    "search_risk_signals"
}

# ── Full list for agents that use .bind_tools() ───────
ALL_TOOLS = [
    search_general,
    search_news,
    search_deep,
    search_risk_signals,
    search_financials
]