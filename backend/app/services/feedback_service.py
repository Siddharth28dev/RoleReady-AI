"""
feedback_service.py
────────────────────
Paper: "The feedback generation module synthesizes analysis results from
        THREE sources into comprehensive, actionable reports:
        1. Resume evaluation
        2. Skill gap identification
        3. Interview response assessment"

Paper: "Feedback organization follows a structured format covering:
        - Resume quality
        - Interview performance
        - Skill development priorities"

Paper: "Positive reinforcement acknowledges existing strengths to build
        candidate confidence while constructive criticism identifies
        specific areas for growth."
"""


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def generate_feedback(
    resume_data:    dict,
    skill_gap_data: dict,
    interview_data: dict,
) -> dict:
    """
    Synthesize feedback from all 3 sources as per paper.

    Args:
        resume_data    : output of parser_service.parse_resume()
        skill_gap_data : output of similarity_service.analyze()
        interview_data : output of evaluation_service.evaluate_multiple_answers()

    Returns:
        Complete structured feedback report
    """

    # ── Source 1: Resume Quality ───────────────────────────────────────────
    resume_feedback = _evaluate_resume_quality(resume_data)

    # ── Source 2: Skill Gap Analysis ──────────────────────────────────────
    skill_feedback = _evaluate_skill_gaps(skill_gap_data)

    # ── Source 3: Interview Performance ───────────────────────────────────
    interview_feedback = _evaluate_interview_performance(interview_data)

    # ── Synthesize overall score from all 3 sources ────────────────────────
    overall = _synthesize_overall(
        resume_feedback, skill_feedback, interview_feedback
        
    )

    # ── Collect all strengths + weaknesses across sources ─────────────────
    all_strengths = (
        resume_feedback["strengths"]
        + skill_feedback["strengths"]
        + interview_feedback["strengths"]
    )
    all_weaknesses = (
        resume_feedback["weaknesses"]
        + skill_feedback["weaknesses"]
        + interview_feedback["weaknesses"]
    )

    return {
        "overall": overall,
        "resume_section": resume_feedback,
        "skill_section":  skill_feedback,
        "interview_section": interview_feedback,
        "strengths":  all_strengths,
        "weaknesses": all_weaknesses,
        "summary":    _generate_summary(overall["score"]),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 1 — RESUME QUALITY
# ══════════════════════════════════════════════════════════════════════════════

def _evaluate_resume_quality(resume_data: dict) -> dict:
    """
    Paper: "Data validation procedures identify potentially missing or
            inconsistent information, flagging areas where candidates
            might strengthen their resumes."

    BUGFIX: resume_data was expected to be the flat dict returned by
    parser_service.parse_resume() (contact/education/projects at the
    top level). But the frontend actually sends the full
    /api/resume/upload response, which nests all of that one level
    deeper under "parsed_data" — only "skills" and "experience" happen
    to be duplicated at the top level. That mismatch made contact,
    education, and projects always read as empty, regardless of what
    the resume actually contained. Unwrap here so it works whether the
    caller passes the full upload response or the flat parsed dict.
    """
    if "parsed_data" in resume_data and "contact" not in resume_data:
        resume_data = resume_data["parsed_data"]
    strengths  = []
    weaknesses = []
    score      = 0
    max_score  = 0

    # ── Contact completeness ──────────────────────────────────────────────
    contact = resume_data.get("contact", {})
    max_score += 20
    contact_score = 0
    if contact.get("email"):
        contact_score += 7
        strengths.append("Email address present in resume.")
    else:
        weaknesses.append("Email address missing — add contact email.")

    if contact.get("phone"):
        contact_score += 7
        strengths.append("Phone number present in resume.")
    else:
        weaknesses.append("Phone number missing — add contact number.")

    if contact.get("linkedin"):
        contact_score += 3
        strengths.append("LinkedIn profile linked.")
    else:
        weaknesses.append("LinkedIn profile missing — add your LinkedIn URL.")

    if contact.get("github"):
        contact_score += 3
        strengths.append("GitHub profile linked.")
    else:
        weaknesses.append("GitHub profile missing — add your GitHub URL.")
    score += contact_score

    # ── Skills section ────────────────────────────────────────────────────
    max_score += 25
    all_skills = resume_data.get("skills", {}).get("all_skills", [])
    if len(all_skills) >= 10:
        score += 25
        strengths.append(f"Strong skills section with {len(all_skills)} skills listed.")
    elif len(all_skills) >= 5:
        score += 15
        strengths.append(f"{len(all_skills)} skills listed — good start.")
        weaknesses.append("Add more relevant technical skills to reach 10+.")
    else:
        score += 5
        weaknesses.append(f"Only {len(all_skills)} skills found — expand your skills section significantly.")

    # ── Education ─────────────────────────────────────────────────────────
    max_score += 20
    education = resume_data.get("education", [])
    if education:
        score += 20
        strengths.append(f"Education section present with {len(education)} entr{'y' if len(education)==1 else 'ies'}.")
    else:
        weaknesses.append("Education section missing or not detected — ensure it is clearly labeled.")

    # ── Experience ────────────────────────────────────────────────────────
    max_score += 20
    experience = resume_data.get("experience", {})
    date_ranges = experience.get("date_ranges", [])
    total_years = experience.get("total_years")
    if date_ranges or total_years:
        score += 20
        if total_years:
            strengths.append(f"Work experience of {total_years} years detected.")
        else:
            strengths.append(f"{len(date_ranges)} experience period(s) detected.")
    else:
        weaknesses.append("Work experience or internship dates not clearly detected — use clear date ranges (e.g. Jan 2022 – Mar 2024).")

    # ── Projects ─────────────────────────────────────────────────────────
    max_score += 15
    projects = resume_data.get("projects", [])
    if len(projects) >= 3:
        score += 15
        strengths.append(f"{len(projects)} projects listed — demonstrates practical experience.")
    elif len(projects) >= 1:
        score += 8
        strengths.append(f"{len(projects)} project(s) listed.")
        weaknesses.append("Add more projects (aim for 3+) to demonstrate practical skills.")
    else:
        weaknesses.append("No projects section detected — add relevant personal or academic projects.")

    resume_score = round((score / max_score) * 100, 1) if max_score else 0

    return {
        "score":      resume_score,
        "rating":     _score_label(resume_score),
        "strengths":  strengths,
        "weaknesses": weaknesses,
        "details": {
            "skills_count":  len(all_skills),
            "education":     len(education),
            "projects":      len(projects),
            "has_linkedin":  bool(contact.get("linkedin")),
            "has_github":    bool(contact.get("github")),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 2 — SKILL GAP ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def _evaluate_skill_gaps(skill_gap_data: dict) -> dict:
    """
    Paper: "Gap analysis identifies skills present in the role specification
            but absent or weakly represented in the candidate profile."
    Paper: "Categorizes gaps as core requirements or preferred qualifications."
    """
    strengths  = []
    weaknesses = []

    scores      = skill_gap_data.get("scores", {})
    combined    = scores.get("combined_score", 0)
    matched     = skill_gap_data.get("matched_skills", [])
    missing     = skill_gap_data.get("missing_skills", [])
    core_gaps   = skill_gap_data.get("missing_core_skills", [])
    pref_gaps   = skill_gap_data.get("missing_preferred_skills", [])

    # Strengths
    if matched:
        strengths.append(
            f"{len(matched)} skill(s) matched with job requirements: "
            f"{', '.join(matched[:5])}{'...' if len(matched)>5 else ''}."
        )
    if combined >= 65:
        strengths.append(
            f"Overall profile match score of {combined}% — strong alignment with role."
        )

    # Weaknesses — core gaps are more urgent
    if core_gaps:
        weaknesses.append(
            f"{len(core_gaps)} CORE skill gap(s) identified (must-have): "
            f"{', '.join(core_gaps[:5])}{'...' if len(core_gaps)>5 else ''}."
        )
    if pref_gaps:
        weaknesses.append(
            f"{len(pref_gaps)} preferred skill gap(s) identified (good-to-have): "
            f"{', '.join(pref_gaps[:3])}{'...' if len(pref_gaps)>3 else ''}."
        )
    if combined < 50:
        weaknesses.append(
            f"Overall match score is {combined}% — significant gap between "
            f"your profile and the job requirements."
        )

    return {
        "score":            combined,
        "rating":           scores.get("rating", "N/A"),
        "strengths":        strengths,
        "weaknesses":       weaknesses,
        "matched_skills":   matched,
        "core_gaps":        core_gaps,
        "preferred_gaps":   pref_gaps,
        "total_required":   skill_gap_data.get("total_required", 0),
        "total_matched":    skill_gap_data.get("total_matched", 0),
        "total_missing":    skill_gap_data.get("total_missing", 0),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 3 — INTERVIEW PERFORMANCE
# ══════════════════════════════════════════════════════════════════════════════

def _evaluate_interview_performance(interview_data: dict) -> dict:
    """
    Paper: "Scoring algorithms aggregate these dimensions into overall
            response ratings while maintaining transparency about specific
            strengths and weaknesses."
    """
    strengths  = []
    weaknesses = []

    if not interview_data:
        return {
            "score":      0,
            "rating":     "Not Attempted",
            "strengths":  [],
            "weaknesses": ["Interview simulation not completed yet."],
            "breakdown":  {},
        }

    overall_score   = interview_data.get("overall_score", 0)
    overall_rating  = interview_data.get("overall_rating", "N/A")
    total_questions = interview_data.get("total_questions", 0)
    summary         = interview_data.get("summary", {})
    breakdown       = summary.get("breakdown", {})
    individual      = interview_data.get("individual_results", [])

    # Strengths
    excellent_count = breakdown.get("excellent", 0)
    good_count      = breakdown.get("good", 0)
    if excellent_count:
        strengths.append(f"{excellent_count} answer(s) rated Excellent.")
    if good_count:
        strengths.append(f"{good_count} answer(s) rated Good.")
    if overall_score >= 75:
        strengths.append(
            f"Strong overall interview score of {overall_score}% — well prepared."
        )

    # Weaknesses
    poor_count    = breakdown.get("poor", 0)
    average_count = breakdown.get("average", 0)
    if poor_count:
        weaknesses.append(
            f"{poor_count} answer(s) rated Poor — needs significant improvement."
        )
    if average_count:
        weaknesses.append(
            f"{average_count} answer(s) rated Average — room for improvement."
        )
    if overall_score < 60:
        weaknesses.append(
            "Overall interview score below 60% — practice structured answers "
            "using the STAR method and include technical terminology."
        )

    # Per-question weak areas
    for r in individual:
        dims = r.get("dimensions", {})
        completeness = dims.get("completeness", {})
        if completeness.get("label") in ["Brief", "Too Short"]:
            weaknesses.append(
                f"Answer to '{r.get('question','')[:60]}...' was too brief "
                f"({completeness.get('word_count', 0)} words). Aim for 50-80+ words."
            )
            break  # Only flag first occurrence to avoid flooding

    return {
        "score":            overall_score,
        "rating":           overall_rating,
        "strengths":        strengths,
        "weaknesses":       weaknesses,
        "total_questions":  total_questions,
        "breakdown":        breakdown,
        "verdict":          summary.get("verdict", ""),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  SYNTHESIZE OVERALL SCORE
# ══════════════════════════════════════════════════════════════════════════════

def _synthesize_overall(
    resume_fb: dict,
    skill_fb:  dict,
    interview_fb: dict,
) -> dict:
    """
    Paper: "Comprehensive feedback covering resume quality,
            interview performance, and identified skill gaps."

    Weights (paper-aligned):
        Resume quality    → 25%
        Skill gap match   → 35%
        Interview score   → 40%
    """
    resume_score    = resume_fb.get("score", 0)
    skill_score     = skill_fb.get("score", 0)
    interview_score = interview_fb.get("score", 0)

    # Skip interview weight if not attempted
    if interview_fb.get("rating") == "Not Attempted":
        overall = round((resume_score * 0.40) + (skill_score * 0.60), 1)
    else:
        overall = round(
            (resume_score    * 0.25) +
            (skill_score     * 0.35) +
            (interview_score * 0.40),
            1
        )

    return {
        "score":   overall,
        "rating":  _score_label(overall),
        "weights": {
            "resume":    "25%",
            "skill_gap": "35%",
            "interview": "40%",
        },
        "component_scores": {
            "resume_quality":     resume_score,
            "skill_match":        skill_score,
            "interview_performance": interview_score,
        },
    }


def _generate_summary(overall_score: float) -> str:
    """Paper: 'Rather than providing only numerical scores,
              the system generates explanatory feedback.'"""
    if overall_score >= 85:
        return (
            "Outstanding! Your profile is exceptionally well-prepared for this role. "
            "Focus on the minor improvements listed to maximize your chances."
        )
    if overall_score >= 70:
        return (
            "Good preparation overall. You have solid foundations — address the "
            "identified skill gaps and practice interview answers to reach the next level."
        )
    if overall_score >= 55:
        return (
            "Moderate preparation. Significant improvements needed in the areas flagged. "
            "Prioritize core skill gaps and practice structured interview responses."
        )
    return (
        "Needs substantial improvement. Focus on building the core skills required "
        "for this role before applying. Use the to-do list below as your action plan."
    )


def _score_label(score: float) -> str:
    if score >= 85: return "Excellent"
    if score >= 70: return "Good"
    if score >= 55: return "Average"
    if score >= 40: return "Weak"
    return "Poor"