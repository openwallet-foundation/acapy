import pytest

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from typing import Mapping

from .. import middleware as test_module


def state(p_parms: Mapping[str, str], q_parms: Mapping[str, str]):
    """Return germane component of mock request app state.

    Args:
        params: p_parms: dict mapping URL path parameters to value
        params: q_parms: dict mapping URL query parameters to value
    """

    test_get_parm_spec = [
        {
            "name": p,
            "in": "path",
            "schema": {"type": "string", "pattern": r"^[a-zA-Z0-9]+$"},
        }
        for p in p_parms or []
    ]
    for q in q_parms or []:
        test_get_parm_spec.append(
            {
                "name": q,
                "in": "query",
                "schema": {"type": "string", "pattern": r"^[a-zA-Z0-9]+$"},
            }
        )

    return {
        "swagger_dict": {
            "paths": {
                "/another/{thing}": {
                    "get": {
                        "parameters": [
                            {
                                "name": "thing",
                                "in": "path",
                                "schema": {
                                    "type": "string",
                                    "pattern": r"^[-_a-zA-Z0-9]+$",
                                },
                            },
                            {
                                "name": "state",
                                "in": "query",
                                "schema": {
                                    "type": "string",
                                    "pattern": r"^[_a-zA-Z0-9]+$",
                                },
                            },
                        ]
                    },
                },
                "/test{}".format(
                    ("/" + "/".join(["{" + p + "}" for p in p_parms]))
                    if p_parms
                    else ""
                ): {
                    "get": {"parameters": test_get_parm_spec},
                    "put": {
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "schema": {
                                    "type": "string",
                                    "pattern": r"^[-_a-zA-Z0-9]+$",
                                },
                            }
                        ]
                    },
                },
            }
        }
    }


class TestMiddleware(AsyncTestCase):
    async def test_check_param_schema_pattern_path(self):
        p_parms = {"id": "abc123"}
        request = async_mock.MagicMock(
            match_info=p_parms,
            path="/test/abc123",
            method="GET",
            query={},
            app=async_mock.MagicMock(_state=state(p_parms, None)),
        )
        handler = async_mock.CoroutineMock(return_value="dummy")
        assert "dummy" == await test_module.check_param_schema_pattern(request, handler)

    async def test_check_param_schema_pattern_path_x(self):
        p_parms = {"id": "abc.123"}  # dot breaks app state schema pattern
        request = async_mock.MagicMock(
            match_info=p_parms,
            path="/test/abc.123",
            method="GET",
            query={},
            app=async_mock.MagicMock(_state=state(p_parms, None)),
        )
        handler = async_mock.CoroutineMock(return_value="dummy")

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.check_param_schema_pattern(request, handler)

    async def test_check_param_schema_pattern_path_x(self):
        p_parms = {"id": "abc.123"}  # dot breaks app state schema pattern
        request = async_mock.MagicMock(
            match_info=p_parms,
            path="/test/abc.123",
            method="GET",
            query={},
            app=async_mock.MagicMock(_state=state(p_parms, None)),
        )
        handler = async_mock.CoroutineMock(return_value="dummy")

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.check_param_schema_pattern(request, handler)

    async def test_check_param_schema_pattern_query(self):
        q_parms = {"id": "abc123"}
        request = async_mock.MagicMock(
            match_info={},
            path="/test",
            method="GET",
            query=q_parms,
            app=async_mock.MagicMock(_state=state(None, q_parms)),
        )
        handler = async_mock.CoroutineMock(return_value="dummy")
        assert "dummy" == await test_module.check_param_schema_pattern(request, handler)

    async def test_check_param_schema_pattern_query_x(self):
        q_parms = {"id": "abc.123"}  # dot breaks app state schema pattern
        request = async_mock.MagicMock(
            match_info={},
            path="/test",
            method="GET",
            query=q_parms,
            app=async_mock.MagicMock(_state=state(None, q_parms)),
        )
        handler = async_mock.CoroutineMock(return_value="dummy")

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.check_param_schema_pattern(request, handler)
