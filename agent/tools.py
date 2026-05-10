import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

load_dotenv()

# TOOL 1: General Web Search 

@tool
def search_general(query: str) -> str:
    """
    Search the web for general information about any topic.
    Use for overview, background, and general facts.
    Best for: Who is X, What is X, Overview of X.

    Args:
        query: search query string

    Returns:
        Formatted string of search results
    """
    tavily  = TavilySearchResults(
        api_key     = os.getenv("TAVILY_API_KEY"),
        max_results = 4,
        search_depth= "basic"
    )
    results = tavily.invoke({"query": query})
    output  = ""
    for i, r in enumerate(results, 1):
        output += f"[{i}] {r['title']}\n"
        output += f"    URL: {r['url']}\n"
        output += f"    {r['content'][:300]}\n\n"
    return output or "No results found."

# TOOL 2: News Search 

@tool
def search_news(query: str) -> str:
    """
    Search specifically for recent news and current events.
    Use for: latest developments, recent controversies,
    current status, news from the past year.

    Args:
        query: news search query

    Returns:
        Formatted string of recent news results
    """
    tavily  = TavilySearchResults(
        api_key      = os.getenv("TAVILY_API_KEY"),
        max_results  = 4,
        search_depth = "advanced",
        topic        = "news"
    )
    results = tavily.invoke({"query": query})
    output  = ""
    for i, r in enumerate(results, 1):
        output += f"[NEWS {i}] {r['title']}\n"
        output += f"    URL: {r['url']}\n"
        output += f"    {r['content'][:300]}\n\n"
    return output or "No news found."

# TOOL 3: Deep Research 

@tool
def search_deep(query: str) -> str:
    """
    Perform deep, thorough research on a specific aspect.
    Use when general search didn't give enough detail.
    Best for: financial data, technical details,
    biographical details, company specifics.

    Args:
        query: detailed research query

    Returns:
        Detailed research results string
    """
    tavily  = TavilySearchResults(
        api_key      = os.getenv("TAVILY_API_KEY"),
        max_results  = 5,
        search_depth = "advanced"
    )
    results = tavily.invoke({"query": query})
    output  = ""
    for i, r in enumerate(results, 1):
        output += f"[DEEP {i}] {r['title']}\n"
        output += f"    URL: {r['url']}\n"
        output += f"    {r['content'][:500]}\n\n"
    return output or "No deep results found."


# TOOL 4: Risk Signals Search

@tool
def search_risk_signals(subject: str) -> str:
    """
    Search specifically for risk signals: controversies,
    legal issues, negative press, fraud allegations,
    regulatory problems, or reputational concerns.
    Always run this tool for any dossier subject.

    Args:
        subject: name of person or company to check

    Returns:
        Risk signal findings as string
    """
    queries = [
        f"{subject} controversy scandal fraud allegations",
        f"{subject} lawsuit regulatory investigation problem"
    ]
    tavily  = TavilySearchResults(
        api_key     = os.getenv("TAVILY_API_KEY"),
        max_results = 3
    )
    output  = ""
    for q in queries:
        results = tavily.invoke({"query": q})
        for r in results:
            output += f"[RISK] {r['title']}\n"
            output += f"    {r['content'][:300]}\n\n"
    return output or "No significant risk signals found."

# All tools in a list for easy import
ALL_TOOLS = [
    search_general,
    search_news,
    search_deep,
    search_risk_signals
]