# ──────────────────────────────────────────────
#  SKILLS DATABASE
# ──────────────────────────────────────────────
 
PROGRAMMING_LANGUAGES = [
    "python", "java", "javascript", "typescript", "c++", "c#", "golang",
    "kotlin", "ruby", "php", "matlab",
    "dart", "perl", "bash", "shell", "powershell",
]
 
WEB_TECHNOLOGIES = [
    "html", "css", "html5", "css3", "react", "reactjs", "react.js",
    "angular", "angularjs", "vue", "vuejs", "vue.js", "nextjs", "next.js",
    "nuxtjs", "svelte", "bootstrap", "tailwind", "tailwindcss", "sass",
    "jquery", "webpack", "vite", "babel",
]
 
BACKEND_FRAMEWORKS = [
    "flask", "django", "fastapi", "express", "expressjs", "node.js", "nodejs",
    "spring", "springboot", "spring boot", "laravel",
    "ruby on rails", "asp.net", "dotnet", ".net", "fiber",
]
 
# Skills that are ambiguous short words — matched only as whole words
# These need special word-boundary checking in the skill extractor
AMBIGUOUS_SKILLS = {
    "go":    "programming_languages",   # "go" inside "MongoDB", "logo"
    "r":     "programming_languages",   # "r" matches everywhere
    "c":     "programming_languages",   # "c" matches everywhere
    "gin":   "backend_frameworks",      # "gin" inside "engineering"
    "less":  "web_technologies",        # "less" is a common English word
    "node":  "backend_frameworks",      # "node" inside "knowledge", "node.js"
    "scala": "programming_languages",   # "scala" inside "scalable"
    "spark": "data_ml",                 # "spark" is a common word
    "rails": "backend_frameworks",      # "rails" inside "guardrails"
    "rust":  "programming_languages",   # "rust" is a common word
    "swift": "programming_languages",   # "swift" is a common word
}
 
DATABASES = [
    "mysql", "postgresql", "postgres", "sqlite", "mongodb", "redis",
    "cassandra", "dynamodb", "oracle", "mssql", "sql server", "firebase",
    "supabase", "elasticsearch", "neo4j",
]
 
CLOUD_DEVOPS = [
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "jenkins", "github actions", "ci/cd", "terraform", "ansible", "nginx",
    "linux", "ubuntu", "git", "github", "gitlab", "bitbucket",
]
 
DATA_ML = [
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "tensorflow", "pytorch", "keras", "scikit-learn",
    "sklearn", "pandas", "numpy", "matplotlib", "seaborn", "opencv",
    "hugging face", "transformers", "bert", "gpt", "llm", "langchain",
    "spark", "hadoop", "tableau", "power bi", "excel",
]
 
SOFT_SKILLS = [
    "communication", "teamwork", "leadership", "problem solving",
    "critical thinking", "time management", "adaptability", "creativity",
    "collaboration", "project management", "agile", "scrum", "kanban",
]
 
# BUGFIX: core CS fundamentals were missing from the skill vocabulary
# entirely. A resume literally listing "Data Structures and Algorithms"
# under a "Core Subjects" heading had no way to be recognized as having
# either skill -- extraction only matches strings that exist in one of
# these lists, so "algorithms" and "data structures" could never appear
# in all_skills, which meant skill-gap matching against a job description
# always flagged them as missing, regardless of what the resume said.
CORE_CS_SUBJECTS = [
    "data structures", "algorithms", "data structures and algorithms",
    "oop", "object oriented programming", "oops",
    "dbms", "database management system",
    "operating system", "operating systems",
    "computer networks", "computer networking",
    "system design", "software engineering",
]
 
# Combined flat list for fast lookup (excludes ambiguous ones — handled separately)
ALL_SKILLS = (
    PROGRAMMING_LANGUAGES
    + WEB_TECHNOLOGIES
    + BACKEND_FRAMEWORKS
    + DATABASES
    + CLOUD_DEVOPS
    + DATA_ML
    + SOFT_SKILLS
    + CORE_CS_SUBJECTS
)
 
# Category reverse lookup (skill → category name) for grouping
SKILL_CATEGORY_MAP = (
    {s: "programming_languages" for s in PROGRAMMING_LANGUAGES}
    | {s: "web_technologies"    for s in WEB_TECHNOLOGIES}
    | {s: "backend_frameworks"  for s in BACKEND_FRAMEWORKS}
    | {s: "databases"           for s in DATABASES}
    | {s: "cloud_devops"        for s in CLOUD_DEVOPS}
    | {s: "data_ml"             for s in DATA_ML}
    | {s: "soft_skills"         for s in SOFT_SKILLS}
    | {s: "core_cs_subjects"    for s in CORE_CS_SUBJECTS}
    | AMBIGUOUS_SKILLS  # ambiguous ones carry their own category
)
 
# ──────────────────────────────────────────────
#  EDUCATION KEYWORDS
# ──────────────────────────────────────────────
 
DEGREE_KEYWORDS = [
    # BUGFIX: bare "be" and "me" removed. They were meant as short forms
    # for "B.E." / "M.E." degrees, but _extract_education() matched them
    # as plain substrings — "be" matched inside "Uber", "me" matched
    # inside "Summer", "Framework", "implemented", turning ordinary
    # Experience-section sentences into fake education entries. "b.e"
    # and "m.e" (with the period) already cover the real degree
    # abbreviation correctly, so the bare forms added false-positive risk
    # without adding any real detection value.
    "b.tech", "btech", "b.e", "bachelor", "b.sc", "bsc",
    "m.tech", "mtech", "m.e", "master", "m.sc", "msc",
    "mba", "phd", "ph.d", "doctorate", "diploma", "10th", "12th",
    "high school", "intermediate",
]
 
# ──────────────────────────────────────────────
#  SECTION HEADER KEYWORDS  (used by text_cleaner)
# ──────────────────────────────────────────────
 
SECTION_HEADERS = {
    "education":    ["education", "academic", "qualification", "degree"],
    # BUGFIX: "professional experience" / "work experience" / "relevant
    # experience" added. Header matching requires the line to START WITH
    # a keyword, and the bare word "experience" alone doesn't match
    # "PROFESSIONAL EXPERIENCE" — an extremely common heading. That meant
    # the Experience section was never recognized as its own section, so
    # all of it silently got appended onto whatever section came before
    # it (Education), which combined with the DEGREE_KEYWORDS substring
    # bug above produced fake education entries out of job/internship text.
    "experience":   ["experience", "professional experience", "work experience",
                      "relevant experience", "work history", "employment", "internship"],
    "skills":       ["skills", "technical skills", "technologies", "competencies"],
    # "technical projects" added — same startswith-matching gap as
    # "professional experience" above: a resume header like "TECHNICAL
    # PROJECTS" doesn't start with the bare word "projects", so it was
    # never recognized and fell through to whatever section came before it.
    "projects":     ["projects", "personal projects", "academic projects", "technical projects"],
    "certifications": ["certifications", "certificates", "courses", "training"],
    # "summary":      ["summary", "objective", "about me", "profile"],
    "contact":      ["contact", "email", "phone", "address", "linkedin", "github"],
}
 
# ──────────────────────────────────────────────
#  JOB ROLE → REQUIRED SKILLS MAPPING
# ──────────────────────────────────────────────
 
JOB_ROLE_SKILLS = {
    "software developer": [
        "python", "java", "javascript", "git", "sql", "data structures",
        "algorithms", "oop", "rest api", "linux",
    ],
    "frontend developer": [
        "html", "css", "javascript", "react", "typescript", "git",
        "responsive design", "rest api", "webpack", "tailwind",
    ],
    "backend developer": [
        "python", "java", "node.js", "flask", "django", "sql", "postgresql",
        "rest api", "docker", "git", "linux",
    ],
    "full stack developer": [
        "html", "css", "javascript", "react", "node.js", "python",
        "sql", "mongodb", "git", "docker", "rest api",
    ],
    "data scientist": [
        "python", "machine learning", "deep learning", "pandas", "numpy",
        "scikit-learn", "tensorflow", "pytorch", "sql", "statistics",
        "data visualization", "jupyter",
    ],
    "data analyst": [
        "python", "sql", "excel", "tableau", "power bi", "statistics",
        "pandas", "data visualization", "r", "communication",
    ],
    "devops engineer": [
        "docker", "kubernetes", "aws", "linux", "git", "ci/cd",
        "terraform", "ansible", "jenkins", "monitoring", "bash",
    ],
    "ml engineer": [
        "python", "machine learning", "deep learning", "tensorflow",
        "pytorch", "mlops", "docker", "sql", "git", "aws",
    ],
}
 
# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}