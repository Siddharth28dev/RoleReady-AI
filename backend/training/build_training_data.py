"""
build_training_data.py
────────────────────────
Rebuilds the FLAN-T5 fine-tuning dataset to fix the four problems found in
Training_Data_Diagnosis.md:

  1. Drops the random cross-category "difference between X and Y" generator
     (was 58% of the old dataset, 83% of its own output was nonsensical).
     Replaces it with a small CURATED list of genuinely comparable
     technology pairs, used sparingly — not as the dataset's backbone.
  2. Every generated target is phrased in second person, addressed to the
     candidate.
  3. No trailing ".?" — every template already ends cleanly in "?".
  4. Covers all 8 roles actually defined in seed_roles.py (the old data was
     99.5% "Software Engineer", a role the app doesn't even offer), all 4
     question types roughly evenly (old data was 80% technical / 0.5%
     situational), and a real spread of skills per role instead of 5
     skills covering 99% of examples.

Keeps the 155 examples from the original dataset that passed every check
in analyze_training_data.py (no flags) — no reason to discard good data.

Usage:
    python build_training_data.py \
        --original training_data_flagged.json \
        --out training_data_v2.json
"""

import argparse
import json
import random


# ══════════════════════════════════════════════════════════════════════════
#  ROLES — matches backend/seed_roles.py exactly (name, default level)
# ══════════════════════════════════════════════════════════════════════════
ROLES = [
    ("Backend Developer", "fresher"),
    ("Frontend Developer", "fresher"),
    ("Full Stack Developer", "mid"),
    ("Data Scientist", "mid"),
    ("ML Engineer", "mid"),
    ("DevOps Engineer", "mid"),
    ("Senior Backend Developer / Tech Lead", "senior"),
    ("Senior Data Scientist / ML Lead", "senior"),
]
LEVELS = ["fresher", "mid", "senior"]

# ══════════════════════════════════════════════════════════════════════════
#  SKILLS PER ROLE — drawn from app/utils/constants.py's real categories,
#  scoped to what's actually relevant per role (a Frontend Developer isn't
#  quizzed on Kubernetes; a Data Scientist isn't quizzed on React).
# ══════════════════════════════════════════════════════════════════════════
ROLE_SKILLS = {
    "Backend Developer": ["python", "java", "flask", "django", "fastapi", "postgresql",
                           "mongodb", "rest api", "docker", "git", "sql", "redis"],
    "Frontend Developer": ["javascript", "typescript", "react", "angular", "vue", "html",
                            "css", "webpack", "rest api", "git", "tailwind"],
    "Full Stack Developer": ["javascript", "python", "react", "node.js", "express", "flask",
                              "postgresql", "mongodb", "docker", "rest api", "git", "aws"],
    "Data Scientist": ["python", "pandas", "numpy", "scikit-learn", "machine learning",
                        "deep learning", "sql", "tensorflow", "pytorch", "tableau", "nlp"],
    "ML Engineer": ["python", "tensorflow", "pytorch", "machine learning", "deep learning",
                     "docker", "kubernetes", "aws", "mlops", "sql", "spark"],
    "DevOps Engineer": ["docker", "kubernetes", "aws", "azure", "terraform", "ansible",
                         "jenkins", "ci/cd", "linux", "git", "nginx"],
    "Senior Backend Developer / Tech Lead": ["system design", "python", "java", "postgresql",
                                              "docker", "kubernetes", "aws", "rest api",
                                              "microservices", "leadership", "mentoring"],
    "Senior Data Scientist / ML Lead": ["machine learning", "deep learning", "python",
                                         "system design", "tensorflow", "pytorch", "aws",
                                         "leadership", "mentoring", "sql"],
}
SOFT_SKILLS = ["communication", "teamwork", "leadership", "problem solving", "adaptability", "collaboration"]

_SKILL_DESC = {
    "python": "Python", "flask": "Flask", "django": "Django", "fastapi": "FastAPI",
    "react": "React", "angular": "Angular", "vue": "Vue.js", "node.js": "Node.js",
    "express": "Express.js", "javascript": "JavaScript", "typescript": "TypeScript",
    "java": "Java", "postgresql": "PostgreSQL", "mongodb": "MongoDB", "sql": "SQL",
    "docker": "Docker", "kubernetes": "Kubernetes", "aws": "AWS", "azure": "Azure",
    "git": "Git", "rest api": "REST API design", "machine learning": "Machine Learning",
    "deep learning": "Deep Learning", "nlp": "Natural Language Processing",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch", "pandas": "Pandas", "numpy": "NumPy",
    "scikit-learn": "scikit-learn", "tableau": "Tableau", "terraform": "Terraform",
    "ansible": "Ansible", "jenkins": "Jenkins", "ci/cd": "CI/CD", "linux": "Linux",
    "nginx": "Nginx", "redis": "Redis", "html": "HTML", "css": "CSS",
    "webpack": "Webpack", "tailwind": "Tailwind CSS", "system design": "system design",
    "microservices": "microservices architecture", "mlops": "MLOps", "spark": "Apache Spark",
}
def desc(skill):
    return _SKILL_DESC.get(skill, skill)


# ══════════════════════════════════════════════════════════════════════════
#  TEMPLATE BANK — every entry is second person / candidate-directed,
#  none need a trailing "?" appended (they're already correct), several
#  phrasings per (type, level) bucket for real training diversity instead
#  of the model memorizing 3 fixed strings.
# ══════════════════════════════════════════════════════════════════════════
TEMPLATES = {
    "technical": {
        "fresher": [
            "What is {skill} and why is it useful for a {role}?",
            "Can you explain the core concepts of {skill} with a simple example?",
            "What are the main features of {skill} that a {role} should know?",
            "How would you explain {skill} to someone new to the field?",
            "What problem does {skill} solve for a {role}?",
        ],
        "mid": [
            "How have you used {skill} in a real {role} project?",
            "What best practices do you follow when working with {skill}?",
            "How would you debug a performance issue involving {skill}?",
            "What trade-offs have you run into while using {skill}?",
            "How do you decide when {skill} is the right tool for the job?",
        ],
        "senior": [
            "How would you design a scalable system using {skill}?",
            "What trade-offs would you weigh before adopting {skill} at scale?",
            "How does {skill} fit into a distributed or microservices architecture?",
            "How would you evaluate whether {skill} is still the right choice as a system grows?",
            "What would you look for when reviewing another engineer's use of {skill}?",
        ],
    },
    "behavioral": {
        "fresher": [
            "Tell me about a project where you used {skill}. What was your role?",
            "Describe a time you had to learn {skill} quickly. How did you approach it?",
            "Tell me about a challenge you faced while working on a {role} project.",
            "Describe a time you asked for help while learning something new. What happened?",
        ],
        "mid": [
            "Tell me about a time you used {skill} to solve a difficult problem at work.",
            "Describe a situation where you disagreed with a technical decision involving {skill}. How did you handle it?",
            "Tell me about a time you had to deliver a {skill}-related feature under a tight deadline.",
            "Describe a time you improved an existing system that used {skill}.",
        ],
        "senior": [
            "Tell me about a time you led a team through a difficult {skill}-related decision.",
            "Describe a situation where you mentored someone who was struggling with {skill}.",
            "Tell me about a time you convinced stakeholders to invest in {skill}. How did you make the case?",
            "Describe a time your judgment about {skill} was wrong. What did you learn?",
        ],
    },
    "situational": {
        "fresher": [
            "If you were asked to use {skill} for the first time on a live project, how would you approach it?",
            "If your {role} task requires {skill} and you get stuck, what would you do?",
            "If you found a bug in code that uses {skill} right before a demo, what would you do?",
        ],
        "mid": [
            "If a {skill}-related feature is failing in production, how would you diagnose it?",
            "If a teammate's {skill} code is causing issues but they're on leave, how would you handle it?",
            "If your manager asked you to add {skill} to an existing {role} project in two days, how would you approach it?",
        ],
        "senior": [
            "If your team disagreed about whether to adopt {skill}, how would you help them decide?",
            "If a critical {skill}-related outage happened during a release, how would you lead the response?",
            "If leadership asked you to evaluate {skill} for company-wide adoption, what would your process be?",
        ],
    },
    "problem_solving": {
        "fresher": [
            "How would you approach debugging unexpected output from {skill} in your {role} project?",
            "Walk me through how you'd learn to use {skill} for a task you've never done before.",
        ],
        "mid": [
            "A {skill}-related query is causing slow performance in production — how would you investigate it?",
            "How would you refactor a {role} codebase to introduce {skill} without breaking existing functionality?",
        ],
        "senior": [
            "How would you architect a {role} system that needs to scale to millions of users using {skill}?",
            "How would you lead a migration of a legacy system to an architecture built around {skill}?",
        ],
    },
}

# Behavioral/soft-skill specific phrasings (used when skill is a soft skill)
SOFT_SKILL_TEMPLATES = {
    "fresher": [
        "Tell me about a time you showed {skill} while working with others.",
        "Describe a situation where {skill} made a difference in a project's outcome.",
    ],
    "mid": [
        "Tell me about a time your {skill} helped resolve a difficult situation at work.",
        "Describe how you've developed your {skill} over the course of a project.",
    ],
    "senior": [
        "Tell me about a time you had to model strong {skill} for a team going through a difficult change.",
        "Describe how you coach others to improve their {skill}.",
    ],
}

# ══════════════════════════════════════════════════════════════════════════
#  CURATED comparison pairs — real, sensible "when would you choose X over
#  Y" alternatives. Small and hand-picked, unlike the old random-pairing
#  generator. Used as a minor supplement, not the dataset's backbone.
# ══════════════════════════════════════════════════════════════════════════
COMPARISON_PAIRS = [
    ("sql", "nosql database", "mid"), ("rest api", "graphql", "mid"),
    ("microservices", "a monolithic architecture", "senior"),
    ("docker", "a traditional virtual machine", "mid"),
    ("tensorflow", "pytorch", "mid"), ("sql", "orm queries", "mid"),
    ("kubernetes", "docker compose", "senior"),
    ("recursion", "an iterative loop", "mid"),
]

def build_comparison_examples():
    out = []
    for a, b, level in COMPARISON_PAIRS:
        target = f"When would you choose {desc(a)} over {b}, and why?"
        out.append({
            "input_text": f"Generate a technical interview question. Skill: {a}. Experience level: {level}. Question:",
            "target_text": target,
            "_meta": {"job_role": "Software Engineer", "skill": a,
                      "experience_level": level, "question_type": "technical"},
        })
    return out


def build_generated_examples(seed):
    rng = random.Random(seed)
    examples = []
    for role, _default_level in ROLES:
        skills = ROLE_SKILLS[role] + rng.sample(SOFT_SKILLS, 2)
        for level in LEVELS:
            for qtype in ("technical", "behavioral", "situational", "problem_solving"):
                bucket_skills = rng.sample(skills, min(3, len(skills)))
                for skill in bucket_skills:
                    if skill in SOFT_SKILLS and qtype == "behavioral":
                        tmpl_list = SOFT_SKILL_TEMPLATES[level]
                    else:
                        tmpl_list = TEMPLATES[qtype][level]
                    # 2 phrasings per (role, level, type, skill) for variety
                    for tmpl in rng.sample(tmpl_list, min(2, len(tmpl_list))):
                        target = tmpl.format(skill=desc(skill), role=role)
                        examples.append({
                            "input_text": (
                                f"Generate a {qtype.replace('_', ' ')} interview question "
                                f"for a {role} role. Skill: {skill}. Experience level: {level}. Question:"
                            ),
                            "target_text": target,
                            "_meta": {"job_role": role, "skill": skill,
                                      "experience_level": level, "question_type": qtype},
                        })
    return examples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--original", default="training_data_flagged.json")
    ap.add_argument("--out", default="training_data_v2.json")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--val-fraction", type=float, default=0.1)
    args = ap.parse_args()

    with open(args.original) as f:
        original = json.load(f)
    original_all = original["train"] + original["validation"]
    kept = [ex for ex in original_all if "_flags" not in ex]
    print(f"Kept {len(kept)} unflagged examples from the original dataset.")

    generated = build_generated_examples(args.seed) + build_comparison_examples()
    print(f"Generated {len(generated)} new examples covering all 8 roles and 4 question types.")

    all_ex = kept + generated
    rng = random.Random(args.seed)
    rng.shuffle(all_ex)

    n_val = int(len(all_ex) * args.val_fraction)
    val = all_ex[:n_val]
    train = all_ex[n_val:]

    out = {
        "train": train,
        "validation": val,
        "stats": {
            "total_pairs": len(all_ex),
            "train_pairs": len(train),
            "val_pairs": len(val),
            "kept_from_original": len(kept),
            "newly_generated": len(generated),
        },
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {len(all_ex)} total examples ({len(train)} train / {len(val)} val) to {args.out}")


if __name__ == "__main__":
    main()