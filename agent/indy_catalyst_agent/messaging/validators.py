from marshmallow import ValidationError


def must_not_be_none(data):
    if data is None:
        raise ValidationError("Data not provided")
