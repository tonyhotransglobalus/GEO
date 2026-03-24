---
description: Score a page's content for AI citation readiness (citability)
---

# GEO Citability Analysis Workflow

// turbo-all

Analyze a specific page to see how likely AI systems are to cite its content.

## Steps

1. **Run the citability scorer**:
   ```
   python scripts/citability_scorer.py <URL>
   ```

2. **Interpret the results** using `skills/geo-citability/SKILL.md`:
   - Score breakdown: Answer Block Quality (30%), Self-Containment (25%), Structural Readability (20%), Statistical Density (15%), Uniqueness (10%)
   - Optimal passage length: 134-167 words
   - Grade scale: A (80+), B (65-79), C (50-64), D (35-49), F (<35)

3. **For each low-scoring block**, provide rewrite suggestions that:
   - Add specific statistics and named sources
   - Make passages self-contained (reduce pronoun usage)
   - Structure as direct answers to questions
   - Target the 134-167 word sweet spot
