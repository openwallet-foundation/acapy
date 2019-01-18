class Lifecycle:
    def __init__(self, service_connection):
        # service_connection should be a connection to an agent driver
        # running on a service "backend"
        pass

    def on_credential_received(self):
        # self.service_connection.send_message(type=on_credential_received, data=...)
        pass
