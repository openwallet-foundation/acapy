# This file supercedes the normal s2i boot process, which is to
# run manage.py migrate and then invoke gunicorn.

import argparse
import os

from aiohttp import web
import django
from api_indy.tob_anchor.boot import (
    init_app, perform_register_services, start_indy_manager,
    run_django, run_reindex, run_migration,
)

parser = argparse.ArgumentParser(description="aiohttp server example")
parser.add_argument('--host', default=os.getenv('HTTP_HOST'))
parser.add_argument('-p', '--port', default=os.getenv('HTTP_PORT'))
parser.add_argument('-s', '--socket', default=os.getenv('SOCKET_PATH'))


if __name__ == '__main__':
    django.setup()

    disable_migrate = os.environ.get('DISABLE_MIGRATE', 'false')
    disconnected = os.environ.get('INDY_DISABLED', 'false')
    skip_indexing = os.environ.get('SKIP_INDEXING_ON_STARTUP', 'false')

    if not disable_migrate or disable_migrate == 'false':
        do_reindex = False
        if not skip_indexing or skip_indexing == 'false':
            os.environ['SKIP_INDEXING_ON_STARTUP'] = 'active'
            do_reindex = True
        run_migration()
        if do_reindex:
            # queue in current asyncio loop
            run_django(run_reindex)

    args = parser.parse_args()
    if not args.socket and not args.port:
        args.port = 8080

    startup = None
    if not disconnected or disconnected == 'false':
        start_indy_manager()
        startup = perform_register_services

    web.run_app(
        init_app(startup),
        host=args.host, port=args.port, path=args.socket,
        handle_signals=True
    )
