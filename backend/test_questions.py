import urllib.request, json

BASE = "http://127.0.0.1:5000/api/interview"

def post(endpoint, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{BASE}/{endpoint}", data=data,
        headers={"Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(req).read())

payload = {
    "job_role":           "Full Stack Python Developer",
    "resume_text":        """
        Siddharth Srivastava - Software Engineer
        B.Tech Computer Science - United Institute of Technology Prayagraj
        Frontend Developer Intern at Rretoriq Communications
        Skills: Python, React, Flask, Node.js, MySQL, MongoDB, Git
    """,
    "matched_skills":     ["python", "flask", "react", "git", "mongodb", "mysql"],
    "skill_gaps":         ["docker", "aws", "rest api", "django"],
    "experience_level":   "fresher",
    "questions_per_type": 3,
}

print("=" * 60)
print("  INTERVIEW QUESTION GENERATION")
print("=" * 60)
print(f"\nGenerating for: {payload['job_role']}")
print("Please wait — T5 loading on first run...\n")

r = post("generate-questions", payload)

if not r["success"]:
    print("ERROR:", r["error"])
    exit()

d = r["data"]
print(f"Job Role        : {d['job_role']}")
print(f"Experience Level: {d['experience_level']}")
print(f"Total Questions : {d['total_questions']}")
print(f"Skill Gaps Focus: {d['skill_gaps_covered']}")
print(f"Focus Skills    : {d['focus_skills']}")

q = d["questions"]

print("\n" + "─" * 60)
print("  TECHNICAL QUESTIONS")
print("─" * 60)
for i, item in enumerate(q.get("technical", []), 1):
    gap_tag = " [SKILL GAP]" if item.get("is_gap") else ""
    print(f"\nQ{i} [{item['difficulty'].upper()}]{gap_tag}")
    print(f"   Skill   : {item['skill']}")
    print(f"   Question: {item['question']}")

print("\n" + "─" * 60)
print("  PROBLEM SOLVING QUESTIONS")
print("─" * 60)
for i, item in enumerate(q.get("problem_solving", []), 1):
    print(f"\nQ{i} [{item['difficulty'].upper()}]")
    print(f"   Question: {item['question']}")

print("\n" + "─" * 60)
print("  BEHAVIORAL QUESTIONS  (STAR Format)")
print("─" * 60)
for i, item in enumerate(q.get("behavioral", []), 1):
    print(f"\nQ{i}")
    print(f"   Question: {item['question']}")
    print(f"   Format  : {item['format']}")

print("\n" + "─" * 60)
print("  SITUATIONAL QUESTIONS")
print("─" * 60)
for i, item in enumerate(q.get("situational", []), 1):
    print(f"\nQ{i} [{item['difficulty'].upper()}]")
    print(f"   Question: {item['question']}")

print("\n" + "=" * 60)
print("  DONE!")
print("=" * 60)