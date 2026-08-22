import urllib.request, json

BASE = "http://127.0.0.1:5000/api/interview"

def post(endpoint, payload):
    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{BASE}/{endpoint}", data=data,
        headers={"Content-Type": "application/json"}
    )
    return json.loads(urllib.request.urlopen(req).read())


# ── Test 1: Single answer evaluation ─────────────────────────────────────────
print("=" * 60)
print("  TEST 1: Single Answer Evaluation (MiniLM)")
print("=" * 60)

r = post("evaluate", {
    "question":         "What is Docker containerization and why is it important for a Full Stack Python Developer?",
    "candidate_answer": "Docker is a platform that allows you to package applications and their dependencies into containers. It ensures the application runs the same way on any machine. As a Python developer, Docker helps in deployment by creating isolated environments so the Flask or Django app works consistently across dev, staging and production.",
    "question_type":    "technical",
    "skill":            "docker",
    "job_role":         "Full Stack Python Developer",
})

e = r["evaluation"]
print(f"\nScore      : {e['score']}%")
print(f"Rating     : {e['rating']}")
print(f"Similarity : {e['similarity']}")
print(f"\nExpected Answer:\n  {e['expected_answer']}")
print(f"\nStrengths:")
for s in e["feedback"]["strengths"]:
    print(f"  + {s}")
print(f"\nImprovements:")
for i in e["feedback"]["improvements"]:
    print(f"  ! {i}")
print(f"\nTip: {e['feedback']['tip']}")

print(f"\nDimensions:")
for dim, val in e["dimensions"].items():
    print(f"  {dim:22} : {val['score']:5.1f}% [{val['label']}]")


# ── Test 2: Multiple answers evaluation ──────────────────────────────────────
print("\n" + "=" * 60)
print("  TEST 2: Full Interview Evaluation (3 Questions)")
print("=" * 60)

r = post("evaluate-all", {
    "answers": [
        {
            "question":         "What is Docker containerization and why is it important?",
            "candidate_answer": "Docker packages apps into containers so they run consistently everywhere. It solves the 'works on my machine' problem.",
            "question_type":    "technical",
            "skill":            "docker",
            "job_role":         "Full Stack Python Developer",
        },
        {
            "question":         "Tell me about a time during your internship when you faced a technical challenge. How did you overcome it?",
            "candidate_answer": "During my internship at Rretoriq, I was asked to build a dynamic pricing page with Node.js APIs. I had never done backend integration before. I studied the Express.js documentation, asked my mentor for guidance, and successfully built and tested the API within 3 days.",
            "question_type":    "behavioral",
            "skill":            "node.js",
            "job_role":         "Full Stack Python Developer",
        },
        {
            "question":         "What would you do if your project deadline is tomorrow and implementing Docker containerization is required but you have never used it before?",
            "candidate_answer": "I would first check Docker documentation and tutorials. Then I would containerize the basic app using a Dockerfile. I would ask teammates or check Stack Overflow if stuck. I would communicate with my manager about progress and any blockers.",
            "question_type":    "situational",
            "skill":            "docker",
            "job_role":         "Full Stack Python Developer",
        },
    ]
})

e = r["evaluation"]
print(f"\nOverall Score  : {e['overall_score']}%")
print(f"Overall Rating : {e['overall_rating']}")
print(f"Verdict        : {e['summary']['verdict']}")
print(f"\nBreakdown:")
for rating, count in e["summary"]["breakdown"].items():
    print(f"  {rating:10}: {count} question(s)")

print(f"\nIndividual Results:")
for i, res in enumerate(e["individual_results"], 1):
    print(f"\n  Q{i}: {res['question'][:70]}...")
    print(f"       Score : {res['score']}% [{res['rating']}]")
    print(f"       Tip   : {res['feedback']['tip']}")