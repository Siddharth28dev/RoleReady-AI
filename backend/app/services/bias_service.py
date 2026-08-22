"""
bias_service.py
────────────────
Paper: "Bias testing examines whether the system produces equitable
        results across demographic groups."
Paper: "Regular audits of system recommendations across diverse
        candidate profiles help identify and remediate potential
        bias issues."
Paper: "Transparency mechanisms explain how AI components reach
        conclusions, enabling candidates to understand and trust
        system recommendations."

Implementation:
    1. Gender bias detection — flag gendered language in JD/feedback
    2. Keyword neutrality check — flag biased terms in questions/feedback
    3. Score consistency audit — check if similar profiles get similar scores
    4. Transparency report — explain how scores were computed
"""

import re


# ══════════════════════════════════════════════════════════════════════════════
#  BIAS WORD LISTS
# ══════════════════════════════════════════════════════════════════════════════

# Gender-coded words (research-backed lists)
MASCULINE_CODED = [
    "aggressive", "ambitious", "analytical", "assertive", "autonomous",
    "competitive", "confident", "decisive", "determined", "dominant",
    "driven", "independent", "leader", "ninja", "rockstar", "strong",
    "superior", "warrior", "champion", "fearless",
]

FEMININE_CODED = [
    "collaborative", "committed", "compassionate", "considerate",
    "cooperative", "dependable", "empathetic", "gentle", "honest",
    "interpersonal", "loyal", "nurturing", "pleasant", "polite",
    "supportive", "sympathetic", "tactful", "trust", "warm",
]

# Potentially exclusionary terms in JDs
EXCLUSIONARY_TERMS = [
    "culture fit", "culture-fit", "young", "energetic team",
    "recent graduate only", "native speaker", "mother tongue",
    "clean-cut", "digital native", "boys", "girls",
]

# Neutral replacements map
NEUTRAL_REPLACEMENTS = {
    "ninja":       "expert",
    "rockstar":    "skilled professional",
    "aggressive":  "results-oriented",
    "dominant":    "highly capable",
    "boys":        "team members",
    "girls":       "team members",
    "young":       "motivated",
    "culture fit": "values-aligned",
}


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def audit_job_description(jd_text: str) -> dict:
    """
    Paper: "Bias testing examines whether the system produces
            equitable results across demographic groups."

    Audit JD text for:
    1. Gender-coded language
    2. Exclusionary terms
    3. Overall bias score
    """
    jd_lower = jd_text.lower()

    masculine_found    = _find_terms(jd_lower, MASCULINE_CODED)
    feminine_found     = _find_terms(jd_lower, FEMININE_CODED)
    exclusionary_found = _find_terms(jd_lower, EXCLUSIONARY_TERMS)

    # Bias score: 0 = neutral, negative = masculine-coded, positive = feminine-coded
    bias_score = len(feminine_found) - len(masculine_found)

    flags       = []
    suggestions = []

    if masculine_found:
        flags.append(f"Masculine-coded words found: {', '.join(masculine_found)}")
        suggestions.append(
            "Consider replacing masculine-coded words to attract diverse candidates."
        )
        for word in masculine_found:
            if word in NEUTRAL_REPLACEMENTS:
                suggestions.append(
                    f"Replace '{word}' with '{NEUTRAL_REPLACEMENTS[word]}'"
                )

    if exclusionary_found:
        flags.append(f"Potentially exclusionary terms found: {', '.join(exclusionary_found)}")
        for term in exclusionary_found:
            if term in NEUTRAL_REPLACEMENTS:
                suggestions.append(
                    f"Replace '{term}' with '{NEUTRAL_REPLACEMENTS[term]}'"
                )

    bias_label = _bias_label(bias_score, masculine_found, feminine_found)

    return {
        "bias_label":          bias_label,
        "bias_score":          bias_score,
        "masculine_coded":     masculine_found,
        "feminine_coded":      feminine_found,
        "exclusionary_terms":  exclusionary_found,
        "flags":               flags,
        "suggestions":         suggestions,
        "is_biased":           len(flags) > 0,
        "transparency_note": (
            "This audit checks for gender-coded and exclusionary language "
            "that research shows can discourage qualified candidates from applying."
        ),
    }


def audit_feedback(feedback_text: str) -> dict:
    """
    Paper: "Regular audits of system recommendations across
            diverse candidate profiles."

    Check feedback/recommendations for biased language.
    """
    feedback_lower = feedback_text.lower()

    masculine_found    = _find_terms(feedback_lower, MASCULINE_CODED)
    exclusionary_found = _find_terms(feedback_lower, EXCLUSIONARY_TERMS)

    flags       = []
    suggestions = []

    if masculine_found:
        flags.append(
            f"Feedback contains potentially biased terms: {', '.join(masculine_found)}"
        )
        suggestions.append("Use neutral, skill-focused language in feedback.")

    if exclusionary_found:
        flags.append(
            f"Feedback contains exclusionary language: {', '.join(exclusionary_found)}"
        )

    return {
        "is_biased":    len(flags) > 0,
        "flags":        flags,
        "suggestions":  suggestions,
        "transparency_note": (
            "Feedback language is audited to ensure recommendations "
            "are skill-focused and free from demographic bias."
        ),
    }


def audit_score_consistency(scores: list) -> dict:
    """
    Paper: "Regular audits of system recommendations across
            diverse candidate profiles help identify and remediate
            potential bias issues."

    Check if scores are consistent — large variance may indicate bias.

    Args:
        scores: list of dicts with keys: profile_id, overall_score
    """
    if not scores or len(scores) < 2:
        return {
            "consistent":   True,
            "message":      "Not enough data for consistency audit (need 2+ profiles).",
            "variance":     0,
            "std_dev":      0,
        }

    score_values = [s.get("overall_score", 0) for s in scores]
    mean         = sum(score_values) / len(score_values)
    variance     = sum((s - mean) ** 2 for s in score_values) / len(score_values)
    std_dev      = variance ** 0.5

    # Flag if std_dev > 20 for similar profiles — potential inconsistency
    is_consistent = std_dev <= 20.0

    return {
        "consistent":      is_consistent,
        "mean_score":      round(mean, 2),
        "std_deviation":   round(std_dev, 2),
        "variance":        round(variance, 2),
        "sample_size":     len(scores),
        "flag":            None if is_consistent else (
            f"High score variance detected (std_dev={round(std_dev,2)}). "
            "Review scoring logic for potential inconsistency."
        ),
        "transparency_note": (
            "Score consistency is monitored to ensure the system "
            "evaluates all candidates fairly and without systematic bias."
        ),
    }


def generate_transparency_report(
    resume_score:    float,
    skill_score:     float,
    interview_score: float,
    overall_score:   float,
) -> dict:
    """
    Paper: "Transparency mechanisms explain how AI components reach
            conclusions, enabling candidates to understand and trust
            system recommendations."

    Explain exactly how the final score was computed.
    """
    return {
        "title":   "How Your Score Was Calculated",
        "weights": {
            "resume_quality":        "25%",
            "skill_gap_match":       "35%",
            "interview_performance": "40%",
        },
        "calculation": {
            "resume_contribution":    round(resume_score    * 0.25, 2),
            "skill_contribution":     round(skill_score     * 0.35, 2),
            "interview_contribution": round(interview_score * 0.40, 2),
            "final_score":            overall_score,
        },
        "explanation": (
            f"Your resume quality scored {resume_score}% (weighted 25%), "
            f"your skill match with the job description scored {skill_score}% "
            f"(weighted 35%), and your interview performance scored "
            f"{interview_score}% (weighted 40%). "
            f"Combined, your overall score is {overall_score}%."
        ),
        "ai_methods_used": [
            "spaCy NER for resume parsing",
            "all-MiniLM-L6-v2 for semantic skill matching",
            "FLAN-T5-base for question and keyword generation",
            "Cosine similarity for answer evaluation",
        ],
        "transparency_note": (
            "All scoring decisions are based purely on skills, experience, "
            "and interview performance. No demographic information is used."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _find_terms(text: str, term_list: list) -> list:
    """Find which terms from a list appear in text using word boundaries."""
    found = []
    for term in term_list:
        pattern = r'\b' + re.escape(term) + r'\b'
        if re.search(pattern, text):
            found.append(term)
    return found


def _bias_label(
    bias_score: int,
    masculine:  list,
    feminine:   list,
) -> str:
    if not masculine and not feminine:
        return "Neutral"
    if bias_score > 2:
        return "Feminine-coded"
    if bias_score < -2:
        return "Masculine-coded"
    return "Slightly Biased"