"""Middleware to validate URL parameters if @docs set pattern in JSON schema."""

import re
from aiohttp import web


@web.middleware
async def check_param_schema_pattern(request, handler):
    """Check URL parameters against schema pattern if specified in @docs decorator."""

    # parameters in path
    for path_template in request.app._state["swagger_dict"]["paths"]:
        try:
            path_candidate = path_template.format(**request.match_info)
            if str(request.path) == path_candidate:
                for p_param in request.match_info:
                    specs = [
                        p
                        for p in request.app._state["swagger_dict"]["paths"][
                            path_template
                        ][request.method.lower()]["parameters"]
                        if p["name"] == p_param and p["in"] == "path"
                    ]
                    if specs:
                        p_pat = specs[0].get("schema", {}).get("pattern")
                        if p_pat and not re.search(p_pat, request.match_info[p_param]):
                            raise web.HTTPBadRequest(
                                reason=f"Non-compliant parameter: {p_param}"
                            )
                break
        except KeyError:
            continue  # path has parameter not in request: not a candidate, carry on

    # parameters in query
    for q_param in request.query:
        specs = [
            p
            for p in request.app._state["swagger_dict"]["paths"][request.path][
                request.method.lower()
            ]["parameters"]
            if p["name"] == q_param and p["in"] == "query"
        ]
        if specs:
            q_pat = specs[0].get("schema", {}).get("pattern")
            if q_pat and not re.search(q_pat, request.query[q_param]):
                raise web.HTTPBadRequest(reason=f"Non-compliant parameter: {q_param}")

    return await handler(request)
