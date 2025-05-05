FROM  postgres:17@sha256:304ab813518754228f9f792f79d6da36359b82d8ecf418096c636725f8c930ad
COPY ./init-postgres-role.sh /docker-entrypoint-initdb.d/init-postgres-role.sh
CMD ["docker-entrypoint.sh", "postgres"]