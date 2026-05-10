# agent/config.py
# ══════════════════════════════════════════════════════
# ALL CONSTANTS AND CONFIG IN ONE PLACE
#
# Change behaviour of the entire agent by editing
# values here — no hunting through node files.
# ══════════════════════════════════════════════════════

# ── LLM SETTINGS ──────────────────────────────────────
LLM_MODEL           = "llama-3.3-70b-versatile"
LLM_TEMP_ANALYTICAL = 0.1     # intake, planner, grader, analyst
LLM_TEMP_CREATIVE   = 0.6     # writer node

# ── SEARCH SETTINGS ───────────────────────────────────
MAX_SEARCH_RESULTS  = 4       # per tool call
MAX_SEARCH_ROUNDS   = 3       # safety valve — max loop iterations
CONTENT_PREVIEW_LEN = 400     # chars of content to keep per result

# ── GRADING THRESHOLDS ────────────────────────────────
GRADE_WRITE_THRESHOLD   = 80  # score >= this → write directly
GRADE_ENRICH_THRESHOLD  = 55  # score >= this → enrich then write
                               # score <  this → re_search

# ── OUTPUT SETTINGS ───────────────────────────────────
OUTPUTS_DIR         = "outputs"
MAX_FINDINGS_FOR_LLM= 4000    # chars of findings sent to writer LLM

# ── RISK LEVELS ───────────────────────────────────────
RISK_ICONS = {
    "LOW"   : "🟢",
    "MEDIUM": "🟡",
    "HIGH"  : "🔴"
}

VERDICT_ICONS = {
    "complete": "✅",
    "partial" : "⚠️",
    "failed"  : "❌"
}