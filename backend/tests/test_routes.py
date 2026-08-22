"""
test_routes.py
──────────────
Integration tests — Flask API routes + Database

Tests every API endpoint and verifies:
  1. HTTP response codes
  2. Response JSON structure
  3. Database records created/updated correctly

Run with:
  cd backend
  python -m pytest tests/ -v
"""

import pytest
import json
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from app.extensions import db
from app.models.user_model import User
from app.models.resume_model import Resume
from app.models.skill_model import Skill, ResumeSkill
from app.models.role_model import Role, RoleSkill
from app.models.skill_gap_model import SkillGap
from app.models.interview_session_model import InterviewSession
from app.models.interview_question_model import InterviewQuestion, QuestionKeyword
from app.models.interview_response_model import InterviewResponse
from app.models.response_evaluation_model import ResponseEvaluation
from app.models.feedback_model import FeedbackReport
from app.models.todo_model import TodoItem


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app():
    """Create test Flask app with in-memory SQLite DB."""
    test_app = create_app()
    test_app.config.update({
        "TESTING":                     True,
        "SQLALCHEMY_DATABASE_URI":     "sqlite:///:memory:",
        "UPLOAD_FOLDER":               "test_uploads",
        "WTF_CSRF_ENABLED":            False,
    })
    os.makedirs("test_uploads", exist_ok=True)

    with test_app.app_context():
        db.create_all()
        _seed_test_data()
        yield test_app
        db.drop_all()

    # Cleanup
    import shutil
    if os.path.exists("test_uploads"):
        shutil.rmtree("test_uploads")


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def app_context(app):
    with app.app_context():
        yield


def _seed_test_data():
    """Seed minimal data needed for tests."""
    # Skills
    skills = ["python", "flask", "react", "docker", "aws", "git", "mongodb", "mysql"]
    for s in skills:
        if not Skill.query.filter_by(skill_name=s).first():
            db.session.add(Skill(skill_name=s))

    # Role
    if not Role.query.filter_by(role_name="Backend Developer").first():
        role = Role(role_name="Backend Developer", description="Builds APIs")
        db.session.add(role)
        db.session.flush()

        # Role skills
        for skill_name in ["python", "flask", "mysql", "docker", "aws"]:
            skill = Skill.query.filter_by(skill_name=skill_name).first()
            if skill:
                db.session.add(RoleSkill(role_id=role.id, skill_id=skill.id, importance="core"))

    db.session.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  1. HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════════════

class TestHealth:
    def test_health_check(self, client):
        """GET /api/health should return 200 OK."""
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "ok"


# ══════════════════════════════════════════════════════════════════════════════
#  2. RESUME ROUTES
# ══════════════════════════════════════════════════════════════════════════════

class TestResumeRoutes:

    def test_resume_ping(self, client):
        """GET /api/resume/ping should return 200."""
        r = client.get("/api/resume/ping")
        assert r.status_code == 200

    def test_upload_no_file(self, client):
        """POST /api/resume/upload without file should return 400."""
        r = client.post("/api/resume/upload", data={})
        assert r.status_code == 400
        data = r.get_json()
        assert data["success"] == False
        assert "error" in data

    def test_upload_invalid_extension(self, client):
        """POST /api/resume/upload with .exe file should return 400."""
        data = {
            "file": (io.BytesIO(b"fake content"), "resume.exe"),
        }
        r = client.post("/api/resume/upload",
                        data=data, content_type="multipart/form-data")
        assert r.status_code == 400
        result = r.get_json()
        assert result["success"] == False

    def test_upload_txt_resume(self, client):
        """POST /api/resume/upload with valid TXT resume should return 200."""
        resume_content = b"""
        John Doe
        john@example.com | +91 9876543210

        EDUCATION
        B.Tech in Computer Science 2023
        XYZ University India

        SKILLS
        Python, Flask, React, MySQL, MongoDB, Git, Docker

        EXPERIENCE
        Software Developer Intern 2023
        ABC Company - Built REST APIs using Flask and Python

        PROJECTS
        Resume Analyzer: Built NLP-based resume tool using Python and spaCy
        """
        data = {
            "file":     (io.BytesIO(resume_content), "test_resume.txt"),
            "job_role": "backend developer",
        }
        r = client.post("/api/resume/upload",
                        data=data, content_type="multipart/form-data")

        assert r.status_code == 200
        result = r.get_json()
        assert result["success"] == True
        assert "parsed_data" in result
        assert "skills" in result["parsed_data"]
        assert "contact" in result["parsed_data"]

    def test_parsed_skills_not_empty(self, client):
        """Resume upload should extract at least some skills."""
        resume_content = b"Python developer with Flask, MySQL, Git, Docker experience."
        data = {
            "file": (io.BytesIO(resume_content), "skills_test.txt"),
        }
        r = client.post("/api/resume/upload",
                        data=data, content_type="multipart/form-data")
        assert r.status_code == 200
        result = r.get_json()
        all_skills = result["parsed_data"]["skills"]["all_skills"]
        assert len(all_skills) > 0

    def test_python_skill_detected(self, client):
        """Python should be detected in resume with Python mentioned."""
        resume_content = b"Experienced Python developer using Flask and Django frameworks."
        data = {"file": (io.BytesIO(resume_content), "python_test.txt")}
        r = client.post("/api/resume/upload",
                        data=data, content_type="multipart/form-data")
        assert r.status_code == 200
        skills = r.get_json()["parsed_data"]["skills"]["all_skills"]
        assert "python" in skills

    def test_false_positive_not_detected(self, client):
        """'scala' should NOT be detected in 'scalable' text."""
        resume_content = b"Building scalable web applications for enterprise clients."
        data = {"file": (io.BytesIO(resume_content), "fp_test.txt")}
        r = client.post("/api/resume/upload",
                        data=data, content_type="multipart/form-data")
        assert r.status_code == 200
        skills = r.get_json()["parsed_data"]["skills"]["all_skills"]
        assert "scala" not in skills


# ══════════════════════════════════════════════════════════════════════════════
#  3. ANALYSIS ROUTES
# ══════════════════════════════════════════════════════════════════════════════

class TestAnalysisRoutes:

    def test_job_titles_returns_list(self, client):
        """GET /api/analysis/job-titles should return list of titles."""
        r = client.get("/api/analysis/job-titles")
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] == True
        assert isinstance(data["job_titles"], list)
        assert data["total"] > 0

    def test_skill_gap_no_body(self, client):
        """POST /api/analysis/skill-gap without body returns 400."""
        r = client.post("/api/analysis/skill-gap",
                        content_type="application/json")
        assert r.status_code == 400

    def test_skill_gap_missing_jd(self, client):
        """POST /api/analysis/skill-gap without jd_text returns 400."""
        r = client.post("/api/analysis/skill-gap",
                        json={"resume_skills": ["python"],
                              "resume_text": "developer"})
        assert r.status_code == 400
        assert r.get_json()["success"] == False

    def test_skill_gap_analysis(self, client):
        """POST /api/analysis/skill-gap with valid data returns analysis."""
        payload = {
            "jd_text": (
                "We need a Python developer with Flask, REST API, MySQL, "
                "Git experience. Docker and AWS knowledge is a plus."
            ),
            "resume_text": (
                "Python developer with Flask, MySQL, Git, GitHub experience. "
                "Built REST APIs and web applications."
            ),
            "resume_skills":    ["python", "flask", "mysql", "git", "github"],
            "experience_level": "fresher",
        }
        r = client.post("/api/analysis/skill-gap", json=payload)
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] == True
        analysis = data["analysis"]
        assert "scores"           in analysis
        assert "matched_skills"   in analysis
        assert "missing_skills"   in analysis
        assert "recommendations"  in analysis

    def test_skill_gap_scores_in_range(self, client):
        """Skill gap scores should be between 0 and 100."""
        payload = {
            "jd_text":       "Python Flask developer needed.",
            "resume_text":   "Python developer with Flask experience.",
            "resume_skills": ["python", "flask"],
        }
        r = client.post("/api/analysis/skill-gap", json=payload)
        assert r.status_code == 200
        scores = r.get_json()["analysis"]["scores"]
        assert 0 <= scores["overall_similarity"] <= 100
        assert 0 <= scores["skill_match_score"]  <= 100
        assert 0 <= scores["combined_score"]     <= 100

    def test_similarity_endpoint(self, client):
        """POST /api/analysis/similarity should return score."""
        r = client.post("/api/analysis/similarity", json={
            "jd_text":     "Python Flask REST API developer.",
            "resume_text": "Python developer with Flask and REST API experience.",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] == True
        assert "similarity_score" in data["similarity"]
        assert "rating" in data["similarity"]


# ══════════════════════════════════════════════════════════════════════════════
#  4. INTERVIEW ROUTES
# ══════════════════════════════════════════════════════════════════════════════

class TestInterviewRoutes:

    def test_interview_ping(self, client):
        """GET /api/interview/ping should return 200."""
        r = client.get("/api/interview/ping")
        assert r.status_code == 200

    def test_generate_questions_missing_role(self, client):
        """POST without job_role should return 400."""
        r = client.post("/api/interview/generate-questions",
                        json={"resume_text": "Python developer"})
        assert r.status_code == 400

    def test_generate_questions_missing_resume(self, client):
        """POST without resume_text should return 400."""
        r = client.post("/api/interview/generate-questions",
                        json={"job_role": "Python Developer"})
        assert r.status_code == 400

    def test_generate_questions_success(self, client):
        """POST with valid data should return 12 questions (4 types × 3)."""
        payload = {
            "job_role":           "Python Developer",
            "resume_text":        "B.Tech intern with Python Flask React Git MySQL MongoDB skills.",
            "matched_skills":     ["python", "flask", "react"],
            "skill_gaps":         ["docker", "aws"],
            "experience_level":   "fresher",
            "questions_per_type": 3,
        }
        r = client.post("/api/interview/generate-questions", json=payload)
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] == True
        questions = data["data"]["questions"]
        assert "technical"       in questions
        assert "problem_solving" in questions
        assert "behavioral"      in questions
        assert "situational"     in questions

    def test_all_4_question_types_present(self, client):
        """All 4 question types must be present in response."""
        payload = {
            "job_role":       "Flask Developer",
            "resume_text":    "Intern with Python and Flask experience.",
            "matched_skills": ["python", "flask"],
            "skill_gaps":     ["docker"],
        }
        r = client.post("/api/interview/generate-questions", json=payload)
        assert r.status_code == 200
        q = r.get_json()["data"]["questions"]
        assert len(q["technical"])       > 0
        assert len(q["problem_solving"]) > 0
        assert len(q["behavioral"])      > 0
        assert len(q["situational"])     > 0

    def test_experience_level_detected(self, client):
        """Experience level should be 'fresher' for intern resume."""
        payload = {
            "job_role":       "Python Developer",
            "resume_text":    "B.Tech intern fresher entry level graduate Python.",
            "matched_skills": ["python"],
            "skill_gaps":     ["docker"],
        }
        r = client.post("/api/interview/generate-questions", json=payload)
        assert r.status_code == 200
        assert r.get_json()["data"]["experience_level"] == "fresher"

    def test_evaluate_single_answer(self, client):
        """POST /api/interview/evaluate should return score and feedback."""
        r = client.post("/api/interview/evaluate", json={
            "question":         "What is Docker containerization and why is it important?",
            "candidate_answer": (
                "Docker is a platform to containerize applications. "
                "It packages code and dependencies together ensuring consistent "
                "environments across development and production systems."
            ),
            "question_type":    "technical",
            "skill":            "docker",
            "job_role":         "Python Developer",
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] == True
        evaluation = data["evaluation"]
        assert "score"      in evaluation
        assert "rating"     in evaluation
        assert "feedback"   in evaluation
        assert "dimensions" in evaluation
        assert 0 <= evaluation["score"] <= 100

    def test_evaluate_empty_answer(self, client):
        """Empty answer should return score 0."""
        r = client.post("/api/interview/evaluate", json={
            "question":         "What is Python?",
            "candidate_answer": "",
            "question_type":    "technical",
            "skill":            "python",
        })
        assert r.status_code == 400

    def test_evaluate_multiple_answers(self, client):
        """POST /api/interview/evaluate-all should return overall score."""
        r = client.post("/api/interview/evaluate-all", json={
            "answers": [
                {
                    "question":         "What is Flask?",
                    "candidate_answer": "Flask is a Python web framework for building APIs.",
                    "question_type":    "technical",
                    "skill":            "flask",
                    "job_role":         "Python Developer",
                },
                {
                    "question":         "Tell me about a challenge you faced.",
                    "candidate_answer": "During my internship I faced a bug in production. I debugged it systematically and fixed it within 2 hours.",
                    "question_type":    "behavioral",
                    "skill":            "python",
                    "job_role":         "Python Developer",
                },
            ]
        })
        assert r.status_code == 200
        data = r.get_json()
        assert data["success"] == True
        evaluation = data["evaluation"]
        assert "overall_score"      in evaluation
        assert "individual_results" in evaluation
        assert len(evaluation["individual_results"]) == 2


# ══════════════════════════════════════════════════════════════════════════════
#  5. DATABASE MODEL TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestDatabaseModels:

    def test_create_user(self, app_context):
        """User should be created and retrievable from DB."""
        user = User(
            name="Test User",
            email="testuser@example.com",
            password_hash="hashed_password_123",
        )
        db.session.add(user)
        db.session.commit()

        fetched = User.query.filter_by(email="testuser@example.com").first()
        assert fetched is not None
        assert fetched.name == "Test User"

    def test_duplicate_email_raises_error(self, app_context):
        """Duplicate email should raise IntegrityError."""
        from sqlalchemy.exc import IntegrityError
        u1 = User(name="A", email="dup@test.com", password_hash="x")
        u2 = User(name="B", email="dup@test.com", password_hash="y")
        db.session.add(u1)
        db.session.commit()
        db.session.add(u2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_create_resume(self, app_context):
        """Resume linked to user should be retrievable."""
        user = User(name="Resume User", email="resume@test.com", password_hash="x")
        db.session.add(user)
        db.session.commit()

        resume = Resume(
            user_id=user.id,
            file_name="cv.pdf",
            resume_text="Python Flask developer",
        )
        db.session.add(resume)
        db.session.commit()

        fetched = Resume.query.filter_by(user_id=user.id).first()
        assert fetched is not None
        assert fetched.file_name == "cv.pdf"

    def test_resume_skills_relationship(self, app_context):
        """ResumeSkill should link resume and skill correctly."""
        user   = User(name="Skills User", email="skills@test.com", password_hash="x")
        db.session.add(user)
        db.session.commit()

        resume = Resume(user_id=user.id, file_name="r.pdf", resume_text="Python developer")
        db.session.add(resume)
        db.session.commit()

        skill = Skill.query.filter_by(skill_name="python").first()
        rs    = ResumeSkill(resume_id=resume.id, skill_id=skill.id)
        db.session.add(rs)
        db.session.commit()

        assert len(resume.resume_skills) == 1
        assert resume.resume_skills[0].skill.skill_name == "python"

    def test_skill_gap_created(self, app_context):
        """SkillGap should link resume and missing skill with severity."""
        user   = User(name="Gap User", email="gap@test.com", password_hash="x")
        db.session.add(user)
        db.session.commit()

        resume = Resume(user_id=user.id, file_name="gap.pdf", resume_text="Python dev")
        db.session.add(resume)
        db.session.commit()

        skill = Skill.query.filter_by(skill_name="docker").first()
        gap   = SkillGap(resume_id=resume.id, skill_id=skill.id, severity="high")
        db.session.add(gap)
        db.session.commit()

        fetched = SkillGap.query.filter_by(resume_id=resume.id).first()
        assert fetched is not None
        assert fetched.severity == "high"
        assert fetched.skill.skill_name == "docker"

    def test_interview_session_created(self, app_context):
        """InterviewSession should be linked to user and resume."""
        user   = User(name="Session User", email="session@test.com", password_hash="x")
        db.session.add(user)
        db.session.commit()

        resume  = Resume(user_id=user.id, file_name="s.pdf", resume_text="dev")
        db.session.add(resume)
        db.session.commit()

        role    = Role.query.filter_by(role_name="Backend Developer").first()
        session = InterviewSession(
            user_id=user.id, resume_id=resume.id,
            role_id=role.id if role else None,
        )
        db.session.add(session)
        db.session.commit()

        fetched = InterviewSession.query.filter_by(user_id=user.id).first()
        assert fetched is not None
        assert fetched.resume_id == resume.id

    def test_interview_question_stored(self, app_context):
        """InterviewQuestion should be stored with correct type."""
        user    = User(name="Q User", email="quser@test.com", password_hash="x")
        db.session.add(user)
        db.session.commit()

        resume  = Resume(user_id=user.id, file_name="q.pdf", resume_text="dev")
        db.session.add(resume)
        db.session.commit()

        session = InterviewSession(user_id=user.id, resume_id=resume.id)
        db.session.add(session)
        db.session.commit()

        question = InterviewQuestion(
            session_id=session.id,
            question_text="What is Flask?",
            question_type="technical",
            difficulty="easy",
            expected_answer="Flask is a Python web framework.",
        )
        db.session.add(question)
        db.session.commit()

        fetched = InterviewQuestion.query.filter_by(session_id=session.id).first()
        assert fetched is not None
        assert fetched.question_type == "technical"
        assert "Flask" in fetched.question_text

    def test_full_evaluation_chain(self, app_context):
        """Test complete chain: session → question → response → evaluation."""
        user    = User(name="Chain User", email="chain@test.com", password_hash="x")
        db.session.add(user)
        db.session.commit()

        resume  = Resume(user_id=user.id, file_name="chain.pdf", resume_text="dev")
        db.session.add(resume)
        db.session.commit()

        session  = InterviewSession(user_id=user.id, resume_id=resume.id)
        db.session.add(session)
        db.session.commit()

        question = InterviewQuestion(
            session_id=session.id,
            question_text="Explain Docker.",
            question_type="technical",
            difficulty="easy",
        )
        db.session.add(question)
        db.session.commit()

        response = InterviewResponse(
            question_id=question.id,
            answer_text="Docker packages apps into containers.",
            response_time=45,
        )
        db.session.add(response)
        db.session.commit()

        evaluation = ResponseEvaluation(
            response_id=response.id,
            semantic_score=78.5,
            keyword_score=70.0,
            grammar_score=95.0,
            completeness_score=65.0,
            final_score=77.1,
            rating="Good",
        )
        db.session.add(evaluation)
        db.session.commit()

        # Verify full chain
        fetched_eval = ResponseEvaluation.query.filter_by(response_id=response.id).first()
        assert fetched_eval is not None
        assert float(fetched_eval.final_score) == 77.1
        assert fetched_eval.rating == "Good"
        assert fetched_eval.response.answer_text == "Docker packages apps into containers."

    def test_feedback_and_todo_chain(self, app_context):
        """Test feedback report and todo items chain."""
        user    = User(name="Todo User", email="todo@test.com", password_hash="x")
        db.session.add(user)
        db.session.commit()

        resume  = Resume(user_id=user.id, file_name="todo.pdf", resume_text="dev")
        db.session.add(resume)
        db.session.commit()

        session  = InterviewSession(user_id=user.id, resume_id=resume.id)
        db.session.add(session)
        db.session.commit()

        feedback = FeedbackReport(
            session_id=session.id,
            strengths="Good Python knowledge",
            weaknesses="Needs Docker and AWS",
            recommendations="Practice containerization",
        )
        db.session.add(feedback)
        db.session.commit()

        todo = TodoItem(
            feedback_id=feedback.id,
            task="Learn Docker fundamentals",
            priority="high",
            status="pending",
            resource_url="https://docs.docker.com",
        )
        db.session.add(todo)
        db.session.commit()

        fetched = TodoItem.query.filter_by(feedback_id=feedback.id).first()
        assert fetched is not None
        assert fetched.priority == "high"
        assert fetched.status == "pending"
        assert "Docker" in fetched.task

    def test_cascade_delete_user(self, app_context):
        """Deleting user should cascade delete resume and sessions."""
        user   = User(name="Delete User", email="delete@test.com", password_hash="x")
        db.session.add(user)
        db.session.commit()

        resume  = Resume(user_id=user.id, file_name="del.pdf", resume_text="dev")
        db.session.add(resume)
        db.session.commit()

        user_id   = user.id
        resume_id = resume.id

        db.session.delete(user)
        db.session.commit()

        assert User.query.get(user_id)   is None
        assert Resume.query.get(resume_id) is None


# ══════════════════════════════════════════════════════════════════════════════
#  6. SERVICE UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestParserService:

    def test_parse_resume_returns_dict(self):
        from app.services.parser_service import parse_resume
        result = parse_resume("Python Flask developer with MySQL and Git experience.")
        assert isinstance(result, dict)
        assert "skills" in result
        assert "contact" in result

    def test_python_detected(self):
        from app.services.parser_service import parse_resume
        result = parse_resume("Experienced Python developer using Flask framework.")
        assert "python" in result["skills"]["all_skills"]

    def test_flask_detected(self):
        from app.services.parser_service import parse_resume
        result = parse_resume("Built REST APIs using Flask web framework.")
        assert "flask" in result["skills"]["all_skills"]

    def test_scala_not_in_scalable(self):
        from app.services.parser_service import parse_resume
        result = parse_resume("Building scalable applications for enterprise.")
        assert "scala" not in result["skills"]["all_skills"]

    def test_email_extracted(self):
        from app.services.parser_service import parse_resume
        result = parse_resume("John Doe\njohn@example.com\nPython developer")
        assert result["contact"]["email"] == "john@example.com"

    def test_phone_extracted(self):
        from app.services.parser_service import parse_resume
        result = parse_resume("Contact: 9876543210\nPython developer")
        assert result["contact"]["phone"] is not None


class TestSimilarityService:

    def test_identical_texts_score_high(self):
        from app.services.similarity_service import jd_resume_score
        result = jd_resume_score(
            "Python Flask developer with REST API experience.",
            "Python Flask developer with REST API experience.",
        )
        assert result["similarity_score"] >= 95.0

    def test_unrelated_texts_score_low(self):
        from app.services.similarity_service import jd_resume_score
        result = jd_resume_score(
            "Python Flask developer needed.",
            "I am a chef who makes Italian food.",
        )
        assert result["similarity_score"] < 50.0

    def test_rating_labels(self):
        from app.services.similarity_service import jd_resume_score
        result = jd_resume_score(
            "Python developer needed.",
            "Python developer with experience.",
        )
        assert result["rating"] in ["Excellent", "Good", "Fair", "Weak", "Poor"]


class TestQuestionService:

    def test_generate_returns_4_types(self):
        from app.services.question_service import generate_interview_questions
        result = generate_interview_questions(
            job_role="Python Developer",
            resume_text="Intern with Python and Flask skills.",
            skill_gaps=["docker", "aws"],
            matched_skills=["python", "flask"],
            experience_level="fresher",
            questions_per_type=2,
        )
        q = result["questions"]
        assert "technical"       in q
        assert "problem_solving" in q
        assert "behavioral"      in q
        assert "situational"     in q

    def test_fresher_detected_from_resume(self):
        from app.services.question_service import generate_interview_questions
        result = generate_interview_questions(
            job_role="Developer",
            resume_text="B.Tech intern fresher entry level.",
            skill_gaps=["docker"],
            matched_skills=["python"],
        )
        assert result["experience_level"] == "fresher"

    def test_senior_detected_from_resume(self):
        from app.services.question_service import generate_interview_questions
        result = generate_interview_questions(
            job_role="Developer",
            resume_text="Senior software architect with 7 years experience.",
            skill_gaps=[],
            matched_skills=["python"],
        )
        assert result["experience_level"] == "senior"

    def test_questions_contain_job_role(self):
        from app.services.question_service import generate_interview_questions
        result = generate_interview_questions(
            job_role="Flask Developer",
            resume_text="Python intern.",
            skill_gaps=["docker"],
            matched_skills=["python"],
            questions_per_type=1,
        )
        all_questions = []
        for qtype in result["questions"].values():
            all_questions.extend([q["question"] for q in qtype])

        # At least some questions should mention the role or related skills
        combined = " ".join(all_questions).lower()
        assert "flask developer" in combined or "docker" in combined or "python" in combined


class TestEvaluationService:

    def test_evaluate_returns_score(self):
        from app.services.evaluation_service import evaluate_answer
        result = evaluate_answer(
            question="What is Docker?",
            candidate_answer="Docker is a containerization platform that packages applications into containers for consistent deployment.",
            question_type="technical",
            skill="docker",
            job_role="Python Developer",
        )
        assert "score"    in result
        assert "rating"   in result
        assert "feedback" in result
        assert 0 <= result["score"] <= 100

    def test_good_answer_scores_higher_than_bad(self):
        from app.services.evaluation_service import evaluate_answer

        good = evaluate_answer(
            question="What is Flask?",
            candidate_answer="Flask is a lightweight Python web framework for building REST APIs. It supports routing, request handling, and Jinja2 templating.",
            question_type="technical",
            skill="flask",
            job_role="Developer",
        )
        bad = evaluate_answer(
            question="What is Flask?",
            candidate_answer="I don't know much about that topic sorry.",
            question_type="technical",
            skill="flask",
            job_role="Developer",
        )
        assert good["score"] > bad["score"]

    def test_evaluate_multiple_returns_overall(self):
        from app.services.evaluation_service import evaluate_multiple_answers
        result = evaluate_multiple_answers([
            {
                "question":         "What is Python?",
                "candidate_answer": "Python is a programming language used for web development and data science.",
                "question_type":    "technical",
                "skill":            "python",
                "job_role":         "Developer",
            },
        ])
        assert "overall_score"      in result
        assert "individual_results" in result
        assert len(result["individual_results"]) == 1