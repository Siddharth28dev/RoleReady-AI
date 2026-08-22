"""
run_parsing_accuracy.py
────────────────────────
Paper, Table 2: "Resume Parsing Accuracy — Target >90% — Method: Automated
validation." This script IS that automated validation — it did not exist
before. It runs the actual production pipeline (file_handler.extract_text_from_file
+ parser_service.parse_resume) against a small set of hand-built resumes
with known-correct answers, and reports real field-level accuracy.

Usage:
    cd backend
    python tests/metrics/run_parsing_accuracy.py

Honesty note: 8 resumes is nowhere near a statistically robust sample —
real research would need dozens-to-hundreds of REAL (not synthetic)
resumes. This tells you whether the pipeline is broken or working; it
does not by itself justify a specific published percentage. Treat the
number this prints as a floor check, not a citable result.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.utils.file_handler import extract_text_from_file
from app.utils.text_cleaner import clean_text
from app.services.parser_service import parse_resume

HERE = os.path.dirname(__file__)
SAMPLES_DIR = os.path.join(HERE, "sample_resumes")
GROUND_TRUTH_PATH = os.path.join(HERE, "ground_truth.json")


def score_one(filename: str, gt: dict) -> dict:
    filepath = os.path.join(SAMPLES_DIR, filename)
    ext = filename.rsplit(".", 1)[-1].lower()

    raw_text = extract_text_from_file(filepath, ext)
    cleaned = clean_text(raw_text)
    parsed = parse_resume(cleaned)

    contact = parsed.get("contact", {})
    checks = {}

    # Contact fields — exact match required
    checks["email"] = (contact.get("email") or "").lower() == (gt["email"] or "").lower()
    checks["phone"] = (contact.get("phone") or None) == (gt["phone"] or None)
    checks["linkedin"] = bool(contact.get("linkedin")) == gt["linkedin_present"]
    checks["github"] = bool(contact.get("github")) == gt["github_present"]

    # Structural fields — count-based (>= expected minimum)
    education = parsed.get("education", [])
    checks["education_count"] = len(education) >= gt["min_education_entries"]

    experience = parsed.get("experience", {})
    date_ranges = experience.get("date_ranges", [])
    checks["experience_dates"] = len(date_ranges) >= gt["min_experience_date_ranges"]

    projects = parsed.get("projects", [])
    checks["projects_count"] = len(projects) >= gt["min_projects"]

    # Skills — recall against the expected set (case-insensitive)
    found_skills = {s.lower() for s in parsed.get("skills", {}).get("all_skills", [])}
    expected_skills = {s.lower() for s in gt["expected_skills"]}
    matched = expected_skills & found_skills
    missed = expected_skills - found_skills
    skill_recall = len(matched) / len(expected_skills) if expected_skills else 1.0
    checks["skills_recall_ok"] = skill_recall >= 0.8  # 80%+ of expected skills found

    field_accuracy = sum(1 for v in checks.values() if v) / len(checks)

    return {
        "file": filename,
        "note": gt["note"],
        "field_accuracy": round(field_accuracy * 100, 1),
        "checks": checks,
        "skill_recall": round(skill_recall * 100, 1),
        "skills_missed": sorted(missed),
        "raw_extracted": {
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "linkedin": contact.get("linkedin"),
            "github": contact.get("github"),
            "education_entries": len(education),
            "experience_date_ranges": date_ranges,
            "projects_found": len(projects),
        },
    }


def main():
    with open(GROUND_TRUTH_PATH) as f:
        ground_truth = json.load(f)

    results = []
    for filename, gt in ground_truth.items():
        try:
            results.append(score_one(filename, gt))
        except Exception as e:
            results.append({
                "file": filename, "note": gt["note"],
                "field_accuracy": 0.0, "error": str(e),
            })

    print("=" * 78)
    print("RESUME PARSING ACCURACY — real pipeline run against known-answer fixtures")
    print("=" * 78)
    for r in results:
        print(f"\n{r['file']}  —  {r['note']}")
        if "error" in r:
            print(f"  CRASHED: {r['error']}")
            continue
        print(f"  field accuracy: {r['field_accuracy']}%   skill recall: {r['skill_recall']}%")
        failed = [k for k, v in r["checks"].items() if not v]
        if failed:
            print(f"  FAILED CHECKS: {failed}")
        if r["skills_missed"]:
            print(f"  skills missed: {r['skills_missed']}")

    valid = [r for r in results if "error" not in r]
    overall = sum(r["field_accuracy"] for r in valid) / len(valid) if valid else 0
    overall_skill_recall = sum(r["skill_recall"] for r in valid) / len(valid) if valid else 0

    print("\n" + "=" * 78)
    print(f"OVERALL FIELD ACCURACY:  {round(overall, 1)}%   (n={len(valid)} resumes, paper target: >90%)")
    print(f"OVERALL SKILL RECALL:    {round(overall_skill_recall, 1)}%")
    print("=" * 78)

    report_path = os.path.join(HERE, "parsing_accuracy_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "overall_field_accuracy": round(overall, 1),
            "overall_skill_recall": round(overall_skill_recall, 1),
            "n_resumes": len(valid),
            "results": results,
        }, f, indent=2)
    print(f"\nFull report written to {report_path}")


if __name__ == "__main__":
    main()