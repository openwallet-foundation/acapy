import logging

from django.db import transaction
from haystack import indexes

LOGGER = logging.getLogger(__name__)


class TxnAwareSearchIndex(indexes.SearchIndex):
    _backend_queue = None

    def __init__(self, *args, **kwargs):
        super(TxnAwareSearchIndex, self).__init__(*args, **kwargs)
        self._transaction_added = {}
        self._transaction_removed = {}
        self._transaction_savepts = None

    def reset(self):
        self._transaction_added = {}
        self._transaction_removed = {}
        self._transaction_savepts = None

    def update_object(self, instance, using=None, **kwargs):
        conn = transaction.get_connection()
        if conn.in_atomic_block:
            if self._transaction_savepts != conn.savepoint_ids:
                self._transaction_savepts = conn.savepoint_ids
                conn.on_commit(self.transaction_committed)
            if self.should_update(instance, **kwargs):
                if not using:
                    using = "default"
                if using not in self._transaction_added:
                    self._transaction_added[using] = {}
                self._transaction_added[using][instance.id] = instance
        else:
            if self._transaction_added or self._transaction_removed:
                # previous transaction must have ended with rollback
                self.reset()
            if self._backend_queue:
                self._backend_queue.add(self.__class__, using, [instance])
            else:
                super(TxnAwareSearchIndex, self).update_object(instance, using, **kwargs)

    def remove_object(self, instance, using=None, **kwargs):
        conn = transaction.get_connection()
        if conn.in_atomic_block:
            if self._transaction_savepts != conn.savepoint_ids:
                self._transaction_savepts = conn.savepoint_ids
                conn.on_commit(self.transaction_committed)
            if not using:
                using = "default"
            if using not in self._transaction_removed:
                self._transaction_removed[using] = {}
            self._transaction_removed[using][instance.id] = instance
        else:
            if self._transaction_added or self._transaction_removed:
                # previous transaction must have ended with rollback
                self.reset()
            if self._backend_queue:
                self._backend_queue.delete(self.__class__, using, [instance])
            else:
                super(TxnAwareSearchIndex, self).remove_object(instance, using, **kwargs)

    def transaction_committed(self):
        conn = transaction.get_connection()
        if conn.in_atomic_block:
            # committed nested transaction - ensure hook is attached
            self._transaction_savepts = conn.savepoint_ids
            conn.on_commit(self.transaction_committed)
        else:
            for using, instances in self._transaction_removed.items():
                if instances:
                    LOGGER.debug("Committing %d deferred Solr delete(s) after transaction.", len(instances))
                    if self._backend_queue:
                        self._backend_queue.delete(self.__class__, using, list(instances.values()))
                    else:
                        backend = self.get_backend(using)
                        if backend is not None:
                            for instance in instances.values():
                                backend.remove(instance)
                        else:
                            LOGGER.error("Failed to get backend.  Unable to commit %d deferred Solr delete(s) after transaction.", len(instances))

            for using, instances in self._transaction_added.items():
                if instances:
                    LOGGER.debug("Committing %d deferred Solr update(s) after transaction", len(instances))
                    if self._backend_queue:
                        self._backend_queue.add(self.__class__, using, list(instances.values()))
                    else:
                        backend = self.get_backend(using)
                        if backend is not None:
                            backend.update(self, instances.values())
                        else:
                            LOGGER.error("Failed to get backend.  Unable to commit %d deferred Solr update(s) after transaction.", len(instances))
            self.reset()
