import re
from typing import List, Optional

def detect_definition_patterns(text: str) -> bool:
    """Detect if a text block starts with a definition pattern."""
    # Patterns like "X is...", "X refers to...", "X refers to...", "X defines..."
    patterns = [
        r"^[A-Z][\w\s-]+\s+is\s+",
        r"^[A-Z][\w\s-]+\s+refers\s+to\s+",
        r"^[A-Z][\w\s-]+\s+defines\s+",
        r"^[A-Z][\w\s-]+\s+means\s+",
        r"^[A-Z][\w\s-]+\s+are\s+",
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.I):
            return True
    return False

def count_statistical_density(text: str) -> int:
    """Count statistics, percentages, dollar amounts, and dates."""
    patterns = [
        r"\d+%",               # Percentages
        r"\$\d+",               # Dollar amounts
        r"\d{4}",               # Years
        r"\d+\s+(days|weeks|months|years|users|tools|integrations)", # Specific quantities
        r"According\s+to\s+",   # Sourced claims
    ]
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, text, re.I))
    return count

def check_entity_grounding(text: str, entities: List[str]) -> int:
    """Count mentions of specific entities (brand, product, experts)."""
    count = 0
    for entity in entities:
        if not entity:
            continue
        # Use word boundaries to avoid partial matches
        pattern = r"\b" + re.escape(entity) + r"\b"
        count += len(re.findall(pattern, text, re.I))
    return count

def is_self_contained(text: str) -> bool:
    """Heuristic for self-containment: starts with a noun phrase, avoids starting with pronouns."""
    # Heuristic: First 10 words shouldn't start with "It", "They", "This" (unless followed by noun), "But", "However"
    weak_starts = ["It ", "They ", "He ", "She ", "This ", "That ", "But ", "However ", "And ", "So "]
    for start in weak_starts:
        if text.strip().startswith(start):
            # Special case for "This [Noun]" which is sometimes okay, but "This is" is bad
            if text.strip().startswith("This is"):
                return False
            return False
    return True

def analyze_block_citability(text: str, brand_name: Optional[str] = None) -> dict:
    """Perform a multi-dimensional citability analysis on a text block."""
    words = text.split()
    word_count = len(words)
    
    if word_count < 20:
        return {"score": 0, "metrics": {}}

    is_def = detect_definition_patterns(text)
    stats_count = count_statistical_density(text)
    entity_count = check_entity_grounding(text, [brand_name] if brand_name else [])
    self_contained = is_self_contained(text)
    
    # Calculate sub-scores based on the GEO Skill rubric
    # Answer Block Quality (30%)
    answer_quality = 100 if is_def else (50 if word_count > 40 else 20)
    
    # Self-Containment (25%)
    containment_score = 100 if self_contained else 30
    
    # Statistical Density (15%) - 5+ per 500 words is 100%
    # scale: 1 per 100 words = 100%
    density_ratio = stats_count / (word_count / 100) if word_count > 0 else 0
    stats_score = min(100, int(density_ratio * 100))
    
    # Entity Grounding (15%) - 1+ mention is good
    entity_score = 100 if entity_count > 0 else 20
    
    # Word count optimization (134-167 words is ideal)
    # We'll factor this into the overall score
    length_bonus = 100 if 134 <= word_count <= 167 else (70 if 50 <= word_count <= 250 else 40)
    
    overall = (
        (answer_quality * 0.35) + 
        (containment_score * 0.25) + 
        (stats_score * 0.20) + 
        (entity_score * 0.10) + 
        (length_bonus * 0.10)
    )
    
    return {
        "score": int(overall),
        "metrics": {
            "is_definition": is_def,
            "stats_count": stats_count,
            "entity_count": entity_count,
            "self_contained": self_contained,
            "word_count": word_count
        }
    }

def get_geo_methods(analysis_result: dict) -> list[dict]:
    """Generate specific GEO methods/recommendations based on analysis results."""
    methods = []
    metrics = analysis_result.get("metrics", {})
    score = analysis_result.get("score", 0)
    
    if not metrics.get("is_definition"):
        methods.append({
            "method": "Definition Patterning",
            "impact": "+2.1x citation rate",
            "recommendation": "Rewrite openings with 'X is...' or 'X refers to...' to help AI systems identify core concepts."
        })
    
    if metrics.get("stats_count", 0) < 2:
        methods.append({
            "method": "Statistical Density",
            "impact": "+40% citation lift",
            "recommendation": "Add specific percentages, dollar amounts, or dated studies to back up every primary claim."
        })
        
    if not metrics.get("self_contained"):
        methods.append({
            "method": "Passage Self-Containment",
            "impact": "RAG Retrieval Wins",
            "recommendation": "Ensure each paragraph replaces pronouns (it, they) with the explicit subject/entity name."
        })

    if score < 50:
        methods.append({
            "method": "Claim-Based Architecture",
            "impact": "Fundamental Extractability",
            "recommendation": "Structure each section as a series of 40-60 word Answer Blocks followed by supporting data."
        })

    return methods
