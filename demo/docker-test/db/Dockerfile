FROM  postgres:16
COPY ./init-postgres-role.sh /docker-entrypoint-initdb.d/init-postgres-role.sh
CMD ["docker-entrypoint.sh", "postgres"]