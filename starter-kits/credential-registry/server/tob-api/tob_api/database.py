"""
    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at
        http://www.apache.org/licenses/LICENSE-2.0
    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""
import os

from django.conf import settings

engines = {
    "sqlite": "django.db.backends.sqlite3",
    "postgresql": "django.db.backends.postgresql_psycopg2",
    "mysql": "django.db.backends.mysql",
}


def config():
    service_name = os.getenv("DATABASE_SERVICE_NAME", "").upper().replace("-", "_")

    if service_name:
        engine = engines.get(os.getenv("DATABASE_ENGINE"), engines["sqlite"])
    else:
        engine = engines["sqlite"]

    name = os.getenv("DATABASE_NAME")

    if not name and engine == engines["sqlite"]:
        name = os.path.join(settings.BASE_DIR, "db.sqlite3")

    return {
        "ENGINE": engine,
        "NAME": name,
        "USER": os.getenv("DATABASE_USER"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD"),
        "HOST": os.getenv("{}_SERVICE_HOST".format(service_name)),
        "PORT": os.getenv("{}_SERVICE_PORT".format(service_name)),
    }
