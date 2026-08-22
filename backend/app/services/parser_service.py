"""
parser_service.py
─────────────────
Core NLP resume parsing using spaCy.
 
Steps performed:
  1. Load spaCy model (en_core_web_sm preferred; falls back to blank 'en')
  2. Extract contact info via regex helpers
  3. Extract candidate name via NER (PERSON entity) or first-line heuristic
  4. Extract skills via EntityRuler pattern matching against constants
  5. Extract education via degree keyword scanning
  6. Extract experience years via regex
  7. Split into logical sections
"""
 
import re
import spacy
from spacy.pipeline import EntityRuler
 
from app.utils.constants import (
    ALL_SKILLS,
    AMBIGUOUS_SKILLS,
    DEGREE_KEYWORDS,
    PROGRAMMING_LANGUAGES,
    WEB_TECHNOLOGIES,
    BACKEND_FRAMEWORKS,
    DATABASES,
    CLOUD_DEVOPS,
    DATA_ML,
    SOFT_SKILLS,
)
from app.utils.text_cleaner import (
    clean_text,
    normalize_text,
    extract_email,
    extract_phone,
    extract_linkedin,
    extract_github,
    split_into_sections,
)
 
 
# ── spaCy model loader (singleton) ────────────────────────────────────────────
 
_nlp = None
 
 
def _get_nlp():
    global _nlp
    if _nlp is not None:
        return _nlp
 
    # Try the full pre-trained model first
    try:
        _nlp = spacy.load("en_core_web_sm")
    except OSError:
        # Fallback: blank English model (no pre-trained vectors/NER,
        # but EntityRuler still works perfectly for skill extraction)
        _nlp = spacy.blank("en")
 
    # Add EntityRuler for skill pattern matching
    # (added BEFORE ner so custom patterns take priority)
    if "entity_ruler" not in _nlp.pipe_names:
        ruler = _nlp.add_pipe("entity_ruler", before="ner") if "ner" in _nlp.pipe_names \
                 else _nlp.add_pipe("entity_ruler")
        _add_skill_patterns(ruler)
 
    return _nlp
 
 
def _add_skill_patterns(ruler):
    """Register every skill from constants as a SKILL entity pattern."""
    patterns = []
    for skill in ALL_SKILLS:
        # Single-token pattern
        patterns.append({"label": "SKILL", "pattern": skill})
        # Multi-token pattern (e.g. "machine learning" → two tokens)
        if " " in skill:
            token_patterns = [{"LOWER": tok} for tok in skill.split()]
            patterns.append({"label": "SKILL", "pattern": token_patterns})
    ruler.add_patterns(patterns)
 
 
# ── Public API ─────────────────────────────────────────────────────────────────
 
def parse_resume(raw_text: str) -> dict:
    """
    Main entry point.  Accepts raw resume text, returns a structured dict.
    """
    cleaned = clean_text(raw_text)
    sections = split_into_sections(cleaned)
    normalized = normalize_text(cleaned)
 
    nlp = _get_nlp()
    doc = nlp(cleaned[:nlp.max_length])   # respect spaCy's token limit
 
    return {
        "contact": _extract_contact(cleaned),
        "name":    _extract_name(cleaned, doc),
        "skills":  _extract_skills(normalized, doc),
        "education":   _extract_education(sections.get("education", ""), cleaned),
        "experience":  _extract_experience(sections.get("experience", ""), cleaned),
        "projects":    _extract_projects(sections.get("projects", "")),
        "certifications": _extract_certifications(sections.get("certifications", "")),
        "summary": sections.get("summary", "").strip() or None,
        "raw_sections": sections,
    }
 
 
# ── Private extractors ─────────────────────────────────────────────────────────
 
def _extract_contact(text: str) -> dict:
    return {
        "email":    extract_email(text),
        "phone":    extract_phone(text),
        "linkedin": extract_linkedin(text),
        "github":   extract_github(text),
    }
 
 
def _extract_name(text: str, doc) -> str | None:
    # Strategy 1: first PERSON entity from NER (needs en_core_web_sm)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text.strip()
 
    # Strategy 2: first non-empty line that looks like a name
    # (2-4 words, no digits, no '@')
    for line in text.splitlines():
        line = line.strip()
        words = line.split()
        if 2 <= len(words) <= 4 and not any(c.isdigit() for c in line) and "@" not in line:
            return line
    return None
 
 
def _extract_skills(normalized_text: str, doc) -> dict:
    """
    Skill matching strategy:
    - ALL skills use word-boundary regex (\b) to prevent false positives
      like 'scala' matching inside 'scalable', or 'go' inside 'MongoDB'
    - EntityRuler NER adds extra confidence for multi-word skills
    """
    # ── Step 1: EntityRuler NER matches (multi-word skills like "machine learning") ──
    ner_skills = {ent.text.lower() for ent in doc.ents if ent.label_ == "SKILL"}
 
    # ── Step 2: Word-boundary regex match for ALL skills ─────────────────────
    # This replaces the old naive substring check (skill in text)
    regex_skills = set()
    for skill in ALL_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, normalized_text):
            regex_skills.add(skill)
 
    # ── Step 3: Word-boundary match for ambiguous short skills ───────────────
    for skill in AMBIGUOUS_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, normalized_text):
            regex_skills.add(skill)
 
    all_found = ner_skills | regex_skills
 
    # ── Step 4: Group by category ─────────────────────────────────────────────
    ambiguous_by_category: dict[str, list] = {}
    for skill, cat in AMBIGUOUS_SKILLS.items():
        if skill in all_found:
            ambiguous_by_category.setdefault(cat, []).append(skill)
 
    def intersect(category_list):
        return sorted(s for s in category_list if s in all_found)
 
    def intersect_with_ambiguous(category_list, cat_name):
        return sorted(set(intersect(category_list)) | set(ambiguous_by_category.get(cat_name, [])))
 
    return {
        "programming_languages": intersect_with_ambiguous(PROGRAMMING_LANGUAGES, "programming_languages"),
        "web_technologies":      intersect_with_ambiguous(WEB_TECHNOLOGIES, "web_technologies"),
        "backend_frameworks":    intersect_with_ambiguous(BACKEND_FRAMEWORKS, "backend_frameworks"),
        "databases":             intersect(DATABASES),
        "cloud_devops":          intersect(CLOUD_DEVOPS),
        "data_ml":               intersect_with_ambiguous(DATA_ML, "data_ml"),
        "soft_skills":           intersect(SOFT_SKILLS),
        "all_skills":            sorted(all_found),
    }
 
 
def _extract_education(education_section: str, full_text: str) -> list[dict]:
    """
    Scan only the education section for degree keywords.
    Falls back to full text only if section is empty.
    Uses similarity-based dedup (not just exact match) to avoid near-duplicates.
    """
    # Prefer the dedicated education section to avoid picking up
    # degree keywords scattered in projects/experience sections
    text_to_scan = education_section.strip() if education_section.strip() else full_text
 
    lines = text_to_scan.splitlines()
    lower_lines = [l.lower() for l in lines]
 
    raw_entries = []
    for i, lower_line in enumerate(lower_lines):
        if any(kw in lower_line for kw in DEGREE_KEYWORDS):
            # Take just this line + one line after (not 3 lines — reduces noise)
            entry_text = " ".join(lines[i: i + 2]).strip()
            if len(entry_text) > 10:
                year = _extract_year(entry_text)
                raw_entries.append({"raw": entry_text, "year": year})
 
    # ── Smart dedup: remove entries whose text is a substring of another ─────
    # This handles cases where line i+2 context produces a superset entry
    unique = []
    texts = [e["raw"] for e in raw_entries]
 
    for i, entry in enumerate(raw_entries):
        is_subset = any(
            entry["raw"] != texts[j] and entry["raw"] in texts[j]
            for j in range(len(texts))
        )
        if not is_subset:
            # Also skip near-duplicates by checking 80% token overlap
            already_covered = False
            for kept in unique:
                tokens_a = set(entry["raw"].lower().split())
                tokens_b = set(kept["raw"].lower().split())
                if len(tokens_a) > 0:
                    overlap = len(tokens_a & tokens_b) / len(tokens_a)
                    if overlap > 0.80:
                        already_covered = True
                        break
            if not already_covered:
                unique.append(entry)
 
    return unique
 
 
def _extract_experience(section_text: str, full_text: str) -> dict:
    """
    Extract total years of experience and individual job entries.
    """
    text_to_search = section_text or full_text
 
    # Total years pattern: "3 years", "2+ years", "5 yrs"
    years_match = re.search(
        r"(\d+\.?\d*)\s*\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)",
        text_to_search, re.IGNORECASE
    )
    total_years = float(years_match.group(1)) if years_match else None
 
    # Find date ranges like "Jan 2022 – Mar 2024", "2021 - 2023",
    # or "01/2026 – 03/2026" (numeric MM/YYYY — not recognized before).
    month_name_pattern = (
        r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\.?\s*\d{4}"
        r"\s*[-–—to]+\s*"
        r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?\.?\s*(?:\d{4}|present|current)"
    )
    numeric_mmyyyy_pattern = (
        r"\d{1,2}/\d{4}\s*[-–—to]+\s*(?:\d{1,2}/\d{4}|present|current)"
    )
    date_ranges = re.findall(
        f"(?:{month_name_pattern}|{numeric_mmyyyy_pattern})",
        text_to_search, re.IGNORECASE
    )
 
    return {
        "total_years": total_years,
        "date_ranges": date_ranges,
        "section_text": section_text.strip() or None,
    }
 
 
def _extract_projects(section_text: str) -> list[str]:
    """Return each non-empty line in the projects section as a project entry."""
    if not section_text:
        return []
    projects = []
    for line in section_text.splitlines():
        line = line.strip()
        # Lines longer than 10 chars that look like a title / description
        if len(line) > 10 and not line.startswith(("•", "-", "*")):
            projects.append(line)
        elif len(line) > 10:
            projects.append(line[1:].strip())
    return projects[:10]  # cap at 10
 
 
def _extract_certifications(section_text: str) -> list[str]:
    if not section_text:
        return []
    certs = []
    for line in section_text.splitlines():
        line = line.strip()
        if len(line) > 5:
            certs.append(line.lstrip("•-* "))
    return certs
 
 
def _extract_year(text: str) -> str | None:
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return match.group(0) if match else None