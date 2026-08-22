"""
run_skill_match_precision.py
──────────────────────────────
Paper, Table 2: "Skill Match Precision — Target >85% — Method: Manual
verification." The paper's own stated method for this metric requires a
HUMAN to check each match — this script cannot fully automate that, and
doesn't pretend to. What it does: runs the actual production semantic
matching (services/similarity_service.analyze — real MiniLM embeddings,
not mocked) against a realistic job description for all 8 sample resumes,
and writes every matched/missing skill pair to a CSV for a human (you) to
mark correct/incorrect — exactly the "manual verification" the paper
itself specifies.

Usage:
    cd backend
    python tests/metrics/run_skill_match_precision.py
    # then open skill_match_for_review.csv, fill in the "correct" column
    # with y/n for each row, save, and re-run with --score to get the
    # real precision number.
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.utils.file_handler import extract_text_from_file
from app.utils.text_cleaner import clean_text
from app.services.parser_service import parse_resume
from app.services.similarity_service import analyze

HERE = os.path.dirname(__file__)
SAMPLES_DIR = os.path.join(HERE, "sample_resumes")
CSV_PATH = os.path.join(HERE, "skill_match_for_review.csv")

# A realistic Backend Developer JD — built from the same skill vocabulary
# the parser actually recognizes (app/utils/constants.py), so a poor score
# here reflects the matching logic, not an unfair/unrecognized-term JD.
JD_TEXT = """
We are hiring a Backend Developer. Required skills: Python, Flask or
Django, PostgreSQL or MySQL, Docker, Git, REST API design, AWS.
Preferred: Kubernetes, Redis, MongoDB, CI/CD experience.
Candidate should have solid experience building and deploying backend
services and working with relational databases.
"""

RESUME_FILES = [
    "resume_01.txt", "resume_02.txt", "resume_03.txt", "resume_04.txt",
    "resume_05.docx", "resume_06.txt", "resume_07.txt", "resume_08.txt",
]


def run():
    rows = []
    for filename in RESUME_FILES:
        filepath = os.path.join(SAMPLES_DIR, filename)
        ext = filename.rsplit(".", 1)[-1].lower()

        raw_text = extract_text_from_file(filepath, ext)
        cleaned = clean_text(raw_text)
        parsed = parse_resume(cleaned)
        resume_skills = parsed.get("skills", {}).get("all_skills", [])

        result = analyze(JD_TEXT, cleaned, resume_skills)

        for pair in result["semantic_pairs"]:
            # BUGFIX: similarity_service.analyze()'s semantic_pairs entries
            # are keyed "required" (the JD skill) and "matched_with" (the
            # resume skill it matched against) — see _match_skills() in
            # similarity_service.py. This was reading "jd_skill"/
            # "resume_skill", which don't exist on that dict, so every row
            # silently wrote empty strings for both columns and the CSV
            # was unreviewable no matter how carefully you filled it in.
            rows.append({
                "resume": filename,
                "jd_skill": pair.get("required", ""),
                "matched_resume_skill": pair.get("matched_with", ""),
                "similarity_score": pair.get("score", ""),
                "correct": "",  # <-- you fill this in: y / n
            })

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "resume", "jd_skill", "matched_resume_skill",
            "similarity_score", "correct",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} matched skill pairs to {CSV_PATH}")
    print("Open it, mark each row's 'correct' column as y or n based on")
    print("whether the semantic match actually makes sense, save, then run:")
    print("  python tests/metrics/run_skill_match_precision.py --score")


def score():
    if not os.path.exists(CSV_PATH):
        print("No CSV found yet — run without --score first.")
        return

    with open(CSV_PATH) as f:
        reader = list(csv.DictReader(f))

    labeled = [r for r in reader if r["correct"].strip().lower() in ("y", "n")]
    if not labeled:
        print("No rows have been labeled yet — fill in the 'correct' column first.")
        return

    correct = sum(1 for r in labeled if r["correct"].strip().lower() == "y")
    precision = correct / len(labeled) * 100

    print(f"Labeled rows: {len(labeled)} / {len(reader)} total matches")
    print(f"SKILL MATCH PRECISION: {round(precision, 1)}%   (paper target: >85%)")

    wrong = [r for r in labeled if r["correct"].strip().lower() == "n"]
    if wrong:
        print("\nMarked incorrect:")
        for r in wrong:
            print(f"  {r['resume']}: JD '{r['jd_skill']}' <-> resume '{r['matched_resume_skill']}' (score {r['similarity_score']})")


if __name__ == "__main__":
    if "--score" in sys.argv:
        score()
    else:
        run()