from concurrent.futures import Future, ThreadPoolExecutor
import logging

from vonx.indy.messages import StoredCredential

from vonx.web.view_helpers import (
    IndyCredentialProcessor,
    IndyCredentialProcessorException,
)

from api_indy.indy.credential import Credential, CredentialException, CredentialManager

from .boot import run_django_proc

LOGGER = logging.getLogger(__name__)


class CredentialProcessorQueue(IndyCredentialProcessor):
    def __init__(self, max_threads=10):
        super(CredentialProcessorQueue, self).__init__()
        self._max_threads = max_threads

    def setup(self, app):
        app["credqueue"] = self
        app.on_startup.append(self.app_start)
        app.on_cleanup.append(self.app_stop)

    async def app_start(self, _app=None):
        self.start()

    async def app_stop(self, _app=None):
        self.stop()

    def start(self):
        self._executor = ThreadPoolExecutor(max_workers=self._max_threads)

    def stop(self):
        self._executor.shutdown(True)

    def start_batch(self) -> object:
        """
        May return batch info used for caching and/or scheduling
        """
        return {"manager": CredentialManager()}

    def get_manager(self, batch_info):
        if batch_info:
            return batch_info["manager"]
        return CredentialManager()

    def process_credential(
            self, stored: StoredCredential, origin_did: str = None, batch_info=None) -> Future:
        """
        Perform credential processing and create related objects.
        Processing can be deferred until end_batch to determine appropriate chunk size,
        currently using naive :class:`ThreadPoolExecutor`
        """
        cred = Credential(stored.cred.cred_data, stored.cred.cred_req_metadata, stored.cred_id)
        credential_manager = self.get_manager(batch_info)
        LOGGER.info("Processing credential %s for DID %s", stored.cred_id, origin_did)
        def proc():
            try:
                return credential_manager.process(cred, origin_did)
            except CredentialException as e:
                raise IndyCredentialProcessorException(str(e)) from e
        return self._executor.submit(run_django_proc, proc)

    def end_batch(self, batch_info):
        """
        Ensure that processing has been kicked off
        """
        pass
