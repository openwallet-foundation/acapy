from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS
from django.db.models import signals

from api_v2.models.Credential import Credential
from icat_cbs.utils.credential import CredentialManager
from tob_api.utils.solrqueue import SolrQueue


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
            signals.post_save.send(
                sender=Credential, instance=credential, using=DEFAULT_DB_ALIAS
            )
