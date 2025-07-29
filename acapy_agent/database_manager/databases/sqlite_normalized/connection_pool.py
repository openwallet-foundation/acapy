import queue
import threading
import sqlite3
import logging
from typing import Optional
import time
import os

try:
    from pysqlcipher3 import dbapi2 as sqlcipher
except ImportError:
    sqlcipher = None

from ..errors import DatabaseError, DatabaseErrorCode

LOGGER = logging.getLogger(__name__)

class ConnectionPool:
    def __init__(
        self,
        db_path: str,
        pool_size: int,
        busy_timeout: float,
        encryption_key: Optional[str] = None,
        journal_mode: str = "WAL",
        locking_mode: str = "NORMAL",
        synchronous: str = "FULL",
        shared_cache: bool = True
    ):
        self.db_path = db_path
        self.pool_size = pool_size
        self.busy_timeout = busy_timeout
        self.encryption_key = encryption_key
        self.journal_mode = journal_mode
        self.locking_mode = locking_mode
        self.synchronous = synchronous
        self.shared_cache = shared_cache
        self.pool = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.connection_ids = {}
        self.connection_count = 0
        self._keep_alive_running = threading.Event()
        self._keep_alive_running.set()
        self.keep_alive_thread = threading.Thread(target=self._keep_alive, daemon=True)
        try:
            for _ in range(pool_size):
                conn = self._create_connection()
                self.pool.put(conn)
            self.keep_alive_thread.start()
        except Exception as e:
            LOGGER.error("Failed to initialize connection pool: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to initialize connection pool",
                actual_error=str(e)
            )

    def _keep_alive(self):
        while self._keep_alive_running.is_set():
            time.sleep(10)
            with self.lock:
                temp_conns = []
                checkpoint_conn = None
                try:
                    checkpoint_conn = sqlite3.connect(self.db_path, check_same_thread=False) if not self.encryption_key else sqlcipher.connect(self.db_path, check_same_thread=False)
                    if self.encryption_key:
                        checkpoint_conn.execute(f"PRAGMA key = '{self.encryption_key}'")
                        checkpoint_conn.execute("PRAGMA cipher_migrate")
                        checkpoint_conn.execute("PRAGMA cipher_compatibility = 4")
                    cursor = checkpoint_conn.cursor()
                    cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except Exception as e:
                    LOGGER.error("Keep-alive WAL checkpoint failed: %s", str(e))
                finally:
                    if checkpoint_conn:
                        checkpoint_conn.close()
                initial_size = self.pool.qsize()
                while not self.pool.empty():
                    try:
                        conn = self.pool.get_nowait()
                        conn_id = self.connection_ids.get(id(conn), -1)
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT 1")
                            cursor.execute("BEGIN")
                            cursor.execute("ROLLBACK")
                            temp_conns.append(conn)
                        except Exception:
                            try:
                                conn.close()
                                del self.connection_ids[id(conn)]
                            except:
                                pass
                            try:
                                new_conn = self._create_connection()
                                temp_conns.append(new_conn)
                            except Exception as e:
                                LOGGER.error("Failed to recreate connection in keep-alive: %s", str(e))
                    except queue.Empty:
                        break
                if len(temp_conns) < initial_size:
                    LOGGER.warning("Lost %d connections during keep-alive", initial_size - len(temp_conns))
                while len(temp_conns) < self.pool_size and self._keep_alive_running.is_set():
                    try:
                        new_conn = self._create_connection()
                        temp_conns.append(new_conn)
                    except Exception as e:
                        LOGGER.error("Failed to restore connection in keep-alive: %s", str(e))
                for conn in temp_conns:
                    try:
                        self.pool.put_nowait(conn)
                    except queue.Full:
                        try:
                            conn.close()
                            del self.connection_ids[id(conn)]
                        except:
                            pass

    def _create_connection(self):
        try:
            if self.encryption_key:
                if sqlcipher is None:
                    raise ImportError("pysqlcipher3 is required for encryption but not installed.")
                conn = sqlcipher.connect(self.db_path, timeout=self.busy_timeout, check_same_thread=False)
                try:
                    conn.execute(f"PRAGMA key = '{self.encryption_key}'")
                    conn.execute("PRAGMA cipher_migrate")
                    conn.execute("PRAGMA cipher_compatibility = 4")
                    conn.execute(f"PRAGMA journal_mode = WAL")
                    conn.execute("PRAGMA foreign_keys = ON;")
                    cursor = conn.cursor()
                    cursor.execute("SELECT count(*) FROM sqlite_master")
                except Exception as e:
                    conn.close()
                    LOGGER.error("SQLCipher initialization failed: %s", str(e))
                    raise
            else:
                conn = sqlite3.connect(self.db_path, timeout=self.busy_timeout, check_same_thread=False)
                conn.execute(f"PRAGMA journal_mode = {self.journal_mode}")
                conn.execute(f"PRAGMA locking_mode = {self.locking_mode}")
                conn.execute(f"PRAGMA synchronous = {self.synchronous}")
                conn.execute("PRAGMA cache_size = -2000" if self.shared_cache else "PRAGMA cache_size = -1000")
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA wal_autocheckpoint = 1000")
            conn_id = self.connection_count
            self.connection_ids[id(conn)] = conn_id
            self.connection_count += 1
            return conn
        except Exception as e:
            LOGGER.error("Failed to create database connection: %s", str(e))
            raise DatabaseError(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                message="Failed to create database connection",
                actual_error=str(e)
            )

    def get_connection(self, timeout: float = 30.0):
        with self.lock:
            try:
                start_time = time.time()
                while time.time() - start_time < timeout:
                    try:
                        conn = self.pool.get(block=False)
                        conn_id = self.connection_ids.get(id(conn), -1)
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT 1")
                            #LOGGER.debug("Connection ID=%d retrieved from pool. Pool size: %d/%d", conn_id, self.pool.qsize(), self.pool_size)
                            return conn
                        except sqlite3.OperationalError:
                            try:
                                conn.close()
                                del self.connection_ids[id(conn)]
                            except:
                                pass
                            try:
                                new_conn = self._create_connection()
                                self.pool.put(new_conn)
                            except Exception as e:
                                LOGGER.error("Failed to recreate connection: %s", str(e))
                            continue
                        except Exception:
                            try:
                                conn.close()
                                del self.connection_ids[id(conn)]
                            except:
                                pass
                            try:
                                new_conn = self._create_connection()
                                self.pool.put(new_conn)
                            except Exception as e:
                                LOGGER.error("Failed to recreate connection: %s", str(e))
                            continue
                    except queue.Empty:
                        time.sleep(0.1)
                LOGGER.error("Connection pool exhausted after %d seconds", timeout)
                raise DatabaseError(
                    code=DatabaseErrorCode.CONNECTION_POOL_EXHAUSTED,
                    message=f"Connection pool exhausted after {timeout} seconds"
                )
            except Exception as e:
                LOGGER.error("Failed to retrieve connection from pool: %s", str(e))
                raise DatabaseError(
                    code=DatabaseErrorCode.CONNECTION_ERROR,
                    message="Failed to retrieve connection from pool",
                    actual_error=str(e)
                )

    def return_connection(self, conn):
        with self.lock:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                self.pool.put(conn)
                LOGGER.debug("Connection ID=%d returned to pool. Pool size: %d/%d", self.connection_ids.get(id(conn), -1), self.pool.qsize(), self.pool_size)
            except Exception:
                try:
                    conn.close()
                    del self.connection_ids[id(conn)]
                except:
                    pass
                try:
                    new_conn = self._create_connection()
                    self.pool.put(new_conn)
                except Exception as e:
                    LOGGER.error("Failed to recreate connection for pool: %s", str(e))
                    raise DatabaseError(
                        code=DatabaseErrorCode.CONNECTION_ERROR,
                        message="Failed to recreate connection for pool",
                        actual_error=str(e)
                    )

    def drain_all_connections(self):
        connections = []
        with self.lock:
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    connections.append(conn)
                except queue.Empty:
                    break
        return connections

    def close(self):
        with self.lock:
            self._keep_alive_running.clear()
            self.keep_alive_thread.join(timeout=15.0)
            checkpoint_conn = None
            try:
                checkpoint_conn = sqlite3.connect(self.db_path, check_same_thread=False) if not self.encryption_key else sqlcipher.connect(self.db_path, check_same_thread=False)
                if self.encryption_key:
                    checkpoint_conn.execute(f"PRAGMA key = '{self.encryption_key}'")
                    checkpoint_conn.execute("PRAGMA cipher_migrate")
                    checkpoint_conn.execute("PRAGMA cipher_compatibility = 4")
                    checkpoint_conn.execute("PRAGMA cipher_memory_security = OFF")
                cursor = checkpoint_conn.cursor()
                cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            finally:
                if checkpoint_conn:
                    try:
                        checkpoint_conn.close()
                    except Exception:
                        pass
            while not self.pool.empty():
                try:
                    conn = self.pool.get_nowait()
                    conn_id = self.connection_ids.get(id(conn), -1)
                    try:
                        conn.close()
                        del self.connection_ids[id(conn)]
                    except Exception:
                        pass
                except queue.Empty:
                    break
            self.connection_ids.clear()