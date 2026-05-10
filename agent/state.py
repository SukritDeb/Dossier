import operator
from typing import TypedDict, List, Annotated, Optional
from pydantic import BaseModel, Field

class DossierReport(BaseModel):
    subject         : str   = Field(description="Name of the subject")
    subject_type    : str   = Field(description="person or company")
    overview        : str   = Field(description="2-3 sentence overview")
    key_facts       : List[str] = Field(description="5 key facts")
    risk_level      : str   = Field(description="LOW, MEDIUM, or HIGH")
    risk_reason     : str   = Field(description="Why this risk level")
    tags            : List[str] = Field(description="3-5 descriptive tags")
    confidence      : int   = Field(description="Confidence score 0-100")
    sources_used    : int   = Field(description="Number of sources used")

class AgentState(TypedDict):
    subject             : str           # what to research
    # PLANNING
    subject_type        : str           # person / company / unknown
    research_plan       : List[str]     # list of angles to research
    # ACCUMULATED
    search_queries      : Annotated[List[str], operator.add]
    raw_findings        : Annotated[List[str], operator.add]
    errors              : Annotated[List[str], operator.add]
    # CONTROL FLOW 
    search_count        : int           # how many searches done
    quality_score       : int           # 0-100 from grader
    routing_decision    : str           # re_search / enrich / write
    # ENRICHMENT 
    enriched_data       : str           # extra context if needed
    # OUTPUT 
    final_report        : Optional[DossierReport]   # Pydantic model
    status              : str           # complete / failed / partial