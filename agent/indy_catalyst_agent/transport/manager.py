import asyncio

from . import BaseTransport

class TransportManager:
    def __init__(self, loop=None):
        self._apps = []
        self.user_supplied_loop = loop is not None
        if loop is None:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop

    def add_transport(self, type, host, port):
        app._set_loop(self.loop)
        self._apps.append(AppWrapper(app, port, self.loop))

    def run_all(self):
        try:
            for app in self._apps:
                app.initialize()
            try:
                for app in self._apps:
                    app.show_info()
                print("(Press CTRL+C to quit)")
                self.loop.run_forever()
            except KeyboardInterrupt:  # pragma: no cover
                pass
            finally:
                for app in self._apps:
                    app.shutdown()
        finally:
            for app in self._apps:
                app.cleanup()

        if not self.user_supplied_loop:
            self.loop.close()
