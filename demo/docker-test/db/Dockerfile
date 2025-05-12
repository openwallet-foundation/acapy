FROM  postgres:17@sha256:864831322bf2520e7d03d899b01b542de6de9ece6fe29c89f19dc5e1d5568ccf
COPY ./init-postgres-role.sh /docker-entrypoint-initdb.d/init-postgres-role.sh
CMD ["docker-entrypoint.sh", "postgres"]