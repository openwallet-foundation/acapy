# this is a "filer" Dockerfile, used to ensure file permissions
# are set correctly on the final image
ARG BASE_IMAGE

FROM $BASE_IMAGE

RUN echo "Fixing permissions in $BASE_IMAGE"

RUN find . -name "*.sh" -exec chmod +x '{}' \;
