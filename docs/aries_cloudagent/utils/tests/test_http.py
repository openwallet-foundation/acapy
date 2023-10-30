import os
import tempfile

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from ..http import fetch, fetch_stream, FetchError, put_file, PutError


class TempFile:
    def __init__(self):
        self.name = None

    def __enter__(self):
        file = tempfile.NamedTemporaryFile(delete=False)
        file.write(b"test")
        file.close()
        self.name = file.name
        return self.name

    def __exit__(self, *args):
        if self.name:
            os.unlink(self.name)


class TestTransportUtils(AioHTTPTestCase):
    async def setUpAsync(self):
        self.fail_calls = 0
        self.succeed_calls = 0
        self.redirects = 0
        await super().setUpAsync()

    async def get_application(self):
        app = web.Application()
        app.add_routes(
            [
                web.get("/fail", self.fail_route),
                web.get("/succeed", self.succeed_route),
                web.put("/fail", self.fail_route),
                web.put("/succeed", self.succeed_route),
                web.put("/redirect", self.redirect_route),
            ]
        )
        return app

    async def fail_route(self, request):
        self.fail_calls += 1
        # avoid aiohttp test server issue: https://github.com/aio-libs/aiohttp/issues/3968
        await request.read()
        raise web.HTTPForbidden()

    async def succeed_route(self, request):
        self.succeed_calls += 1
        ret = web.json_response([True])
        return ret

    async def redirect_route(self, request):
        if self.redirects > 0:
            self.redirects -= 1
            # avoid aiohttp test server issue: https://github.com/aio-libs/aiohttp/issues/3968
            await request.read()
            raise web.HTTPRedirection(f"http://localhost:{self.server.port}/success")
        return await self.succeed_route(request)

    async def test_fetch_stream(self):
        server_addr = f"http://localhost:{self.server.port}"
        stream = await fetch_stream(
            f"{server_addr}/succeed", session=self.client.session
        )
        result = await stream.read()
        assert result == b"[true]"
        assert self.succeed_calls == 1

    async def test_fetch_stream_default_client(self):
        server_addr = f"http://localhost:{self.server.port}"
        stream = await fetch_stream(f"{server_addr}/succeed")
        result = await stream.read()
        assert result == b"[true]"
        assert self.succeed_calls == 1

    async def test_fetch_stream_fail(self):
        server_addr = f"http://localhost:{self.server.port}"
        with self.assertRaises(FetchError):
            await fetch_stream(
                f"{server_addr}/fail",
                max_attempts=2,
                interval=0,
                session=self.client.session,
            )
        assert self.fail_calls == 2

    async def test_fetch(self):
        server_addr = f"http://localhost:{self.server.port}"
        result = await fetch(
            f"{server_addr}/succeed", session=self.client.session, json=True
        )
        assert result == [1]
        assert self.succeed_calls == 1

    async def test_fetch_default_client(self):
        server_addr = f"http://localhost:{self.server.port}"
        result = await fetch(f"{server_addr}/succeed", json=True)
        assert result == [1]
        assert self.succeed_calls == 1

    async def test_fetch_fail(self):
        server_addr = f"http://localhost:{self.server.port}"
        with self.assertRaises(FetchError):
            result = await fetch(
                f"{server_addr}/fail",
                max_attempts=2,
                interval=0,
                session=self.client.session,
            )
        assert self.fail_calls == 2

    async def test_put_file_with_session(self):
        server_addr = f"http://localhost:{self.server.port}"
        with TempFile() as tails:
            result = await put_file(
                f"{server_addr}/succeed",
                {"tails": tails},
                {"genesis": "..."},
                session=self.client.session,
                json=True,
            )
        assert result == [True]
        assert self.succeed_calls == 1

    async def test_put_file_default_client(self):
        server_addr = f"http://localhost:{self.server.port}"
        with TempFile() as tails:
            result = await put_file(
                f"{server_addr}/succeed",
                {"tails": tails},
                {"genesis": "..."},
                json=True,
            )
        assert result == [True]
        assert self.succeed_calls == 1

    async def test_put_file_fail(self):
        server_addr = f"http://localhost:{self.server.port}"
        with TempFile() as tails:
            with self.assertRaises(PutError):
                _ = await put_file(
                    f"{server_addr}/fail",
                    {"tails": tails},
                    {"genesis": "..."},
                    max_attempts=2,
                    json=True,
                )
        assert self.fail_calls == 2

    async def test_put_file_redirect(self):
        server_addr = f"http://localhost:{self.server.port}"
        self.redirects = 1
        with TempFile() as tails:
            result = await put_file(
                f"{server_addr}/redirect",
                {"tails": tails},
                {"genesis": "..."},
                max_attempts=2,
                json=True,
            )
        assert result == [True]
        assert self.succeed_calls == 1
        assert self.redirects == 0
