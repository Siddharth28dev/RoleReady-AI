from marshmallow import Schema, fields, validate


class ResumeUploadSchema(Schema):
    job_role = fields.Str(
        required=False,
        load_default=None,
        validate=validate.Length(max=100),
    )


class ContactSchema(Schema):
    email    = fields.Str(allow_none=True)
    phone    = fields.Str(allow_none=True)
    linkedin = fields.Str(allow_none=True)
    github   = fields.Str(allow_none=True)


class SkillsSchema(Schema):
    programming_languages = fields.List(fields.Str())
    web_technologies      = fields.List(fields.Str())
    backend_frameworks    = fields.List(fields.Str())
    databases             = fields.List(fields.Str())
    cloud_devops          = fields.List(fields.Str())
    data_ml               = fields.List(fields.Str())
    soft_skills           = fields.List(fields.Str())
    # BUGFIX: parser_service._extract_skills() was extended to also return
    # core_cs_subjects and declared_skills, but this schema was never
    # updated to declare them. Marshmallow's Schema.dump() silently DROPS
    # any field not explicitly declared here — so both fields were being
    # computed correctly on the backend and then discarded before ever
    # reaching the frontend, which is why "declared_skills" always showed
    # up empty (0) downstream in feedback_service, no matter what the
    # resume's Skills section actually contained.
    core_cs_subjects      = fields.List(fields.Str())
    all_skills            = fields.List(fields.Str())
    declared_skills       = fields.List(fields.Str())


class EducationEntrySchema(Schema):
    raw  = fields.Str()
    year = fields.Str(allow_none=True)


class ExperienceSchema(Schema):
    total_years  = fields.Float(allow_none=True)
    date_ranges  = fields.List(fields.Str())
    section_text = fields.Str(allow_none=True)


# BUGFIX: _extract_projects() was rewritten to group lines into
# {"title": ..., "lines": [...]} entries instead of returning flat
# strings, but this schema still declared `projects` as
# fields.List(fields.Str()) — a type mismatch that would silently mangle
# or error on the field during serialization. Matches the new shape now.
class ProjectEntrySchema(Schema):
    title = fields.Str(allow_none=True)
    lines = fields.List(fields.Str())


class ParsedResumeSchema(Schema):
    contact          = fields.Nested(ContactSchema)
    name             = fields.Str(allow_none=True)
    skills           = fields.Nested(SkillsSchema)
    education        = fields.List(fields.Nested(EducationEntrySchema))
    experience       = fields.Nested(ExperienceSchema)
    projects         = fields.List(fields.Nested(ProjectEntrySchema))
    certifications   = fields.List(fields.Str())
    summary          = fields.Str(allow_none=True)