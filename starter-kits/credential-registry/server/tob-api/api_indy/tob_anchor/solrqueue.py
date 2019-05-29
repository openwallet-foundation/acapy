from datetime import datetime
import logging
from queue import Empty, Full, Queue
import threading

from haystack.utils import get_identifier

from api_v2.search.index import TxnAwareSearchIndex

LOGGER = logging.getLogger(__name__)


class SolrQueue:
    def __init__(self):
        self._queue = Queue()
        self._prev_queue = None
        self._stop = threading.Event()
        self._thread = None
        self._trigger = threading.Event()

    def add(self, index_cls, using, instances):
        ids = [instance.id for instance in instances]
        LOGGER.debug("Solr queue add %s", ids)
        try:
            self._queue.put( (index_cls, using, ids, 0) )
        except Full:
            LOGGER.warning("Solr queue full")

    def delete(self, index_cls, using, instances):
        ids = [get_identifier(instance) for instance in instances]
        LOGGER.debug("Solr queue delete %s", ids)
        try:
            self._queue.put( (index_cls, using, ids, 1) )
        except Full:
            LOGGER.warning("Solr queue full")

    def setup(self, app=None):
        if app:
            app["solrqueue"] = self
            app.on_startup.append(self.app_start)
            app.on_cleanup.append(self.app_stop)
        self._prev_queue = TxnAwareSearchIndex._backend_queue
        TxnAwareSearchIndex._backend_queue = self

    async def app_start(self, _app=None):
        self.start()

    async def app_stop(self, _app=None):
        self.stop()

    def __enter__(self):
        self.setup()
        self.start()
        return self

    def __exit__(self, type, value, tb):
        # if handling exception, don't wait for worker thread
        self.stop(not type)
        TxnAwareSearchIndex._backend_queue = self._prev_queue

    def start(self):
        self._thread = threading.Thread(target=self._run)
        self._thread.start()

    def stop(self, join=True):
        self._stop.set()
        self._trigger.set()
        if join:
            self._thread.join()

    def trigger(self):
        self._trigger.set()

    def _run(self):
        while True:
            self._trigger.wait(5)
            self._drain()
            if self._stop.is_set():
                return

    def _drain(self):
        last_index = None
        last_using = None
        last_del = 0
        last_ids = set()
        while True:
            try:
                index_cls, using, ids, delete = self._queue.get_nowait()
            except Empty:
                index_cls = None
            if last_index and last_index == index_cls and last_using == using and last_del == delete:
                last_ids.update(ids)
            else:
                if last_index:
                    if last_del:
                        self.remove(last_index, last_using, last_ids)
                    else:
                        self.update(last_index, last_using, last_ids)
                if not index_cls:
                    break
                last_index = index_cls
                last_using = using
                last_del = delete
                last_ids = set(ids)

    def update(self, index_cls, using, ids):
        index = index_cls()
        backend = index.get_backend(using)
        if backend is not None:
            LOGGER.debug("Updating %d row(s) in solr queue: %s", len(ids), ids)
            rows = index.index_queryset(using).filter(id__in=ids)
            backend.update(index, rows)
        else:
            LOGGER.error("Failed to get backend.  Unable to update %d row(s) in solr queue: %s", len(ids), ids)

    def remove(self, index_cls, using, ids):
        index = index_cls()
        backend = index.get_backend(using)
        if backend is not None:
            LOGGER.debug("Removing %d row(s) in solr queue: %s", len(ids), ids)
            # backend.remove has no support for a list of IDs
            backend.conn.delete(id=ids)
        else:
            LOGGER.error("Failed to get backend.  Unable to update %d row(s) in solr queue: %s", len(ids), ids)
