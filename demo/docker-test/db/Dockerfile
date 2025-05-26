FROM  postgres:17@sha256:6efd0df010dc3cb40d5e33e3ef84acecc5e73161bd3df06029ee8698e5e12c60
COPY ./init-postgres-role.sh /docker-entrypoint-initdb.d/init-postgres-role.sh
CMD ["docker-entrypoint.sh", "postgres"]