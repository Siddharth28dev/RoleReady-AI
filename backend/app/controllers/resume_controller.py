from flask import current_app
from app.utils.file_handler import allowed_file, save_upload, extract_text_from_file, delete_upload
from app.utils.text_cleaner import clean_text
from app.services.parser_service import parse_resume
from app.schemas.resume_schema import ParsedResumeSchema
from app.extensions import db
from app.models import Resume, Skill, ResumeSkill


def handle_resume_upload(file, job_role: str | None, user_id: int) -> tuple[dict, int]:
    if not file or file.filename == "":
        return {"success": False, "error": "No file provided"}, 400

    if not allowed_file(file.filename):
        return {"success": False, "error": "Invalid file type. Allowed: pdf, docx, txt"}, 400

    try:
        upload_info = save_upload(file, current_app.config["UPLOAD_FOLDER"])
    except Exception as e:
        return {"success": False, "error": f"File save failed: {str(e)}"}, 500

    try:
        raw_text = extract_text_from_file(
            upload_info["filepath"], upload_info["extension"]
        )
    except Exception as e:
        return {"success": False, "error": f"Text extraction failed: {str(e)}"}, 422
    finally:
        # encryption_service.py documents the data-handling promise as
        # "Files -> UUID filename + deleted after parse". The raw file is
        # only ever needed for this one extraction call — everything
        # downstream (parse_resume, persistence) works off raw_text, not
        # the file on disk — so it's deleted here whether extraction
        # succeeded or raised, instead of being left behind indefinitely.
        delete_upload(upload_info["filepath"])

    if not raw_text.strip():
        return {"success": False, "error": "Could not extract text from file"}, 422

    try:
        parsed = parse_resume(raw_text)
    except Exception as e:
        return {"success": False, "error": f"NLP parsing failed: {str(e)}"}, 500

    schema     = ParsedResumeSchema()
    serialized = schema.dump(parsed)

    # ── Persist the Resume row — this used to never happen at all. ──────────
    # Everything downstream (skill_gap_by_role persistence, interview
    # sessions) is FK'd to resumes.id, so this is the load-bearing fix.
    resume_id = None
    try:
        resume = Resume(
            user_id     = user_id,
            file_name   = upload_info["original_name"],
            resume_text = raw_text,
            education   = str(serialized.get("education", "")),
            experience  = str(serialized.get("experience", "")),
        )
        db.session.add(resume)
        db.session.flush()  # assigns resume.id without committing yet

        all_skills = serialized.get("skills", {}).get("all_skills", [])
        for skill_name in all_skills:
            skill = Skill.query.filter_by(skill_name=skill_name).first()
            if not skill:
                skill = Skill(skill_name=skill_name)
                db.session.add(skill)
                db.session.flush()
            db.session.add(ResumeSkill(resume_id=resume.id, skill_id=skill.id))

        db.session.commit()
        resume_id = resume.id
    except Exception as e:
        db.session.rollback()
        # Don't fail the whole upload over a persistence hiccup — the
        # candidate still gets their parsed results — but log it loudly,
        # since a None resume_id here silently breaks every later stage.
        current_app.logger.error(f"Resume persistence failed: {e}")

    return {
        "success":    True,
        "resume_id":  resume_id,
        "file_info": {
            "original_name": upload_info["original_name"],
            "extension":     upload_info["extension"],
        },
        "job_role":    job_role,
        "parsed_data": serialized,
        "parsed_text": raw_text,
        "skills":      serialized.get("skills", {}),
        "experience":  serialized.get("experience", {}),
    }, 200


def handle_get_parsed_text(file, job_role: str | None) -> tuple[dict, int]:
    if not file or file.filename == "":
        return {"success": False, "error": "No file provided"}, 400

    if not allowed_file(file.filename):
        return {"success": False, "error": "Invalid file type"}, 400

    upload_info = None
    try:
        upload_info = save_upload(file, current_app.config["UPLOAD_FOLDER"])
        raw_text    = extract_text_from_file(
            upload_info["filepath"], upload_info["extension"]
        )
        cleaned     = clean_text(raw_text)
    except Exception as e:
        return {"success": False, "error": str(e)}, 500
    finally:
        # Same cleanup contract as handle_resume_upload — see comment there.
        if upload_info:
            delete_upload(upload_info["filepath"])

    return {"success": True, "raw_text": cleaned}, 200