from .....messaging.valid import UUID4_EXAMPLE

test_conn_id = UUID4_EXAMPLE


class MockConnRecord:
    def __init__(self, connection_id, is_ready) -> None:
        self.connection_id = connection_id
        self.is_ready = is_ready
