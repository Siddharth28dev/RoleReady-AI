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
    all_skills            = fields.List(fields.Str())


class EducationEntrySchema(Schema):
    raw  = fields.Str()
    year = fields.Str(allow_none=True)


class ExperienceSchema(Schema):
    total_years  = fields.Float(allow_none=True)
    date_ranges  = fields.List(fields.Str())
    section_text = fields.Str(allow_none=True)


class ParsedResumeSchema(Schema):
    contact          = fields.Nested(ContactSchema)
    name             = fields.Str(allow_none=True)
    skills           = fields.Nested(SkillsSchema)
    education        = fields.List(fields.Nested(EducationEntrySchema))
    experience       = fields.Nested(ExperienceSchema)
    projects         = fields.List(fields.Str())
    certifications   = fields.List(fields.Str())
    summary          = fields.Str(allow_none=True)
