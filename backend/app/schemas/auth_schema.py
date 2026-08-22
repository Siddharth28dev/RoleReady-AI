from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    name     = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    email    = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))


class LoginSchema(Schema):
    email    = fields.Email(required=True)
    password = fields.Str(required=True)