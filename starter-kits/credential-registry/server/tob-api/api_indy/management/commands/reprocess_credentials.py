from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, DEFAULT_DB_ALIAS
from django.db.models import signals

from api_indy.indy.credential import CredentialManager

from api_v2.models.Address import Address
from api_v2.models.Attribute import Attribute
from api_v2.models.Credential import Credential
from api_v2.models.Name import Name

from api_indy.tob_anchor.solrqueue import SolrQueue


class Command(BaseCommand):
    help = "Reprocesses all credentials to populate search database"

    def handle(self, *args, **options):
        queue = SolrQueue()
        with queue:
            self.reprocess(queue, *args, **options)

    def reprocess(self, queue, *args, **options):
        self.stdout.write("Starting...")

        cred_count = Credential.objects.count()
        self.stdout.write("Reprocessing {} credentials".format(cred_count))

        current_cred = 0
        mgr = CredentialManager()
        for credential in Credential.objects.all().iterator():
            current_cred += 1
            self.stdout.write(
                "Processing credential id: {} ({} of {})".format(
                    credential.id, current_cred, cred_count
                )
            )

            # Remove and recreate search records
            mgr.reprocess(credential)

            # Now reindex
            signals.post_save.send(sender=Credential, instance=credential, using=DEFAULT_DB_ALIAS)
