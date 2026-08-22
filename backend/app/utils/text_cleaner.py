import re
from app.utils.constants import SECTION_HEADERS


def clean_text(text: str) -> str:
    """Remove noise from raw extracted text."""
    # Collapse multiple spaces / tabs
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ newlines into two
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def normalize_text(text: str) -> str:
    """Lowercase + strip punctuation for skill matching."""
    text = text.lower()
    text = re.sub(r"[^\w\s\.\+\#]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_email(text: str) -> str | None:
    # \s* around '@' handles a real pdfplumber artifact: an icon glyph
    # placed right before the email in the PDF sometimes throws off its
    # spacing calculation, extracting "name @gmail.com" with a stray
    # space before the @. A plain email has no such space, so this is
    # safe either way.
    match = re.search(r"[\w\.-]+\s*@\s*[\w\.-]+\.\w{2,}", text)
    return match.group(0).replace(" ", "").lower() if match else None


def extract_phone(text: str) -> str | None:
    # Matches Indian (+91) and general formats
    match = re.search(
        r"(\+91[\s\-]?)?[6-9]\d{9}|(\+\d{1,3}[\s\-]?)?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}",
        text,
    )
    return match.group(0).strip() if match else None


def extract_linkedin(text: str) -> str | None:
    match = re.search(r"linkedin\.com/in/[\w\-]+", text, re.IGNORECASE)
    return match.group(0).lower() if match else None


def extract_github(text: str) -> str | None:
    match = re.search(r"github\.com/[\w\-]+", text, re.IGNORECASE)
    return match.group(0).lower() if match else None


def split_into_sections(text: str) -> dict:
    """
    Heuristically split resume text into labelled sections.
    Returns a dict like: { "education": "...", "skills": "...", ... }

    BUGFIX: header matching used to be "keyword anywhere in the line",
    which meant a company name like "DataWorks Technologies" or
    "CloudNext Technologies" — extremely common in Indian resumes —
    would falsely match the "skills" header keyword "technologies" and
    truncate the experience section right after the job title, losing
    the company name, dates, and description. Real section headers are
    a short line that STARTS WITH the keyword (e.g. "SKILLS",
    "Technical Skills", "Skills & Tools") — a company name that merely
    contains the word does not. Matching on startswith instead of
    substring-anywhere fixes this without missing real headers.
    """
    sections = {key: "" for key in SECTION_HEADERS}
    sections["other"] = ""

    lines = text.splitlines()
    current_section = "other"

    for line in lines:
        lower = line.lower().strip()
        # Strip leading bullets/numbering ("• Skills", "1. Skills") so
        # the startswith check still catches those as real headers.
        lower_for_match = re.sub(r"^[\W_]+", "", lower)
        matched = False
        for section, keywords in SECTION_HEADERS.items():
            if any(lower_for_match.startswith(kw) for kw in keywords) and len(lower) < 50:
                current_section = section
                matched = True
                break
        if not matched:
            sections[current_section] += line + "\n"

    return {k: v.strip() for k, v in sections.items()}