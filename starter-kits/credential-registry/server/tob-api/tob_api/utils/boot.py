#
# Copyright 2017-2018 Government of Canada
# Public Services and Procurement Canada - buyandsell.gc.ca
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Importing this file causes the standard settings to be loaded
and a standard service manager to be created. This allows services
to be properly initialized before the webserver process has forked.
"""

import asyncio
import logging
import os

import django.db

from wsgi import application

LOGGER = logging.getLogger(__name__)


def run_django_proc(proc, *args):
    try:
        return proc(*args)
    finally:
        django.db.connections.close_all()


def run_django(proc, *args) -> asyncio.Future:
    return asyncio.get_event_loop().run_in_executor(None, run_django_proc, proc, *args)


def run_reindex():
    from django.core.management import call_command

    batch_size = os.getenv("SOLR_BATCH_SIZE", 500)
    call_command(
        "update_index", "--max-retries=5", "--batch-size={}".format(batch_size)
    )


def run_migration():
    from django.core.management import call_command

    call_command("migrate")


async def add_server_headers(request, response):
    host = os.environ.get("HOSTNAME")
    if host and "X-Served-By" not in response.headers:
        response.headers["X-Served-By"] = host


async def init_app(on_startup=None, on_cleanup=None):
    from aiohttp.web import Application
    from aiohttp_wsgi import WSGIHandler
    from tob_api.utils.solrqueue import SolrQueue

    wsgi_handler = WSGIHandler(application)
    app = Application()
    # all requests forwarded to django
    app.router.add_route("*", "/{path_info:.*}", wsgi_handler)

    solrqueue = SolrQueue()
    solrqueue.setup(app)

    if on_startup:
        app.on_startup.append(on_startup)
    if on_cleanup:
        app.on_cleanup.append(on_cleanup)
    no_headers = os.environ.get("DISABLE_SERVER_HEADERS")
    if not no_headers or no_headers == "false":
        app.on_response_prepare.append(add_server_headers)

    return app
