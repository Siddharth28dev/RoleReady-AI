import urllib.request, json

resume_text = """
Siddharth Srivastava - Software Engineer
Skills: Python, JavaScript, React, Node.js, Flask, MySQL, MongoDB,
Git, GitHub, Tailwind CSS, NLP, Transformers, HTML, CSS, Express.js
Projects: AI Resume Analyzer, Voice Billing System, Docqify AI
Experience: Frontend Developer Intern - React, Tailwind CSS, Node.js APIs
Education: B.Tech Computer Science - United Institute of Technology Prayagraj
"""

jd_text = """
We are looking for a Full Stack Python Developer.
Requirements:
- Strong Python and JavaScript skills
- Experience with React and Node.js
- Backend development with Flask or Django
- Database: MySQL or MongoDB
- REST API design and development
- Git version control
- Problem solving skills
- Bonus: Docker, AWS, TypeScript
"""

resume_skills = [
    "python", "flask", "react", "git", "github", "javascript",
    "mongodb", "mysql", "node.js", "tailwind", "html", "css",
    "nlp", "transformers", "express"
]

BASE = "http://127.0.0.1:5000/api/analysis"

def post(endpoint, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{BASE}/{endpoint}", data=data,
        headers={"Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(req).read())

print("=" * 55)
print("  TEST 1: JD vs Resume Semantic Similarity")
print("=" * 55)
r = post("similarity", {"jd_text": jd_text, "resume_text": resume_text})
s = r["similarity"]
print(f"Score          : {s['similarity_score']}%")
print(f"Rating         : {s['rating']}")
print(f"Interpretation : {s['interpretation']}")

print()
print("=" * 55)
print("  TEST 2: Full Skill Gap Analysis")
print("=" * 55)
r = post("skill-gap", {
    "jd_text":       jd_text,
    "resume_text":   resume_text,
    "resume_skills": resume_skills,
})
a = r["analysis"]

print(f"\nOverall Sim    : {a['scores']['overall_similarity']}%")
print(f"Skill Score    : {a['scores']['skill_match_score']}%")
print(f"Combined Score : {a['scores']['combined_score']}%")
print(f"Rating         : {a['scores']['rating']}")
print(f"Interpretation : {a['scores']['interpretation']}")

print(f"\nJD Required Skills ({a['total_required']}):")
for s in a["jd_required_skills"]:
    print(f"  - {s}")

print(f"\nMatched Skills ({a['total_matched']}):")
for s in a["matched_skills"]:
    print(f"  + {s}")

print(f"\nMissing Skills ({a['total_missing']}):")
for s in a["missing_skills"]:
    print(f"  x {s}")

print("\nSemantic Pairs:")
for p in a["semantic_pairs"]:
    tag = "[EXACT]   " if p["type"] == "exact" else "[SEMANTIC]"
    print(f"  {tag} {p['required']:22} <- {p['matched_with']:20} ({p['score']}%)")

print("\nRecommendations:")
for rec in a["recommendations"]:
    print(f"  {rec['skill']:22} -> {rec['resource']}")