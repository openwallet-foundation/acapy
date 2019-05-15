from django.db import transaction
from api_v2.models import Credential, Name

data = [
    {
        "name": "Test Corp",
    },
    {
        "name": "Testing Corp",
    },
    {
        "name": "Test, Corp",
    },
    {
        "name": "Tested, Corp",
    },
    {
        "name": "Retest Corp",
    },
    {
        "name": "Re-test Corp",
    },
    {
        "name": "Test-Corp",
    },
    {
        "name": "Corp Test",
    },
    {
        "name": "Corp, Test",
    },
    {
        "name": "Test.Corp",
    },
    {
        "name": "Test,Corp",
    },
    {
        "name": "Test+Corp",
    },
    {
        "name": "Te-st Corp",
    },
    {
        "name": "Other Corp",
    },
]


def init_db():
    Credential.objects.all().delete()
    for row in data:
        # use transaction so that the name is added before the credential is indexed
        with transaction.atomic():
            cred = Credential.objects.create(credential_type_id=1, topic_id=1, latest=True)
            # cred.save()
            name = cred.names.create(text=row["name"])
