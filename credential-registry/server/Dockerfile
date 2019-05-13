# this is a "filer" Dockerfile, used to ensure file permissions
# are set correctly on the final tob-api (django) image
FROM django:latest

RUN find . -name "*.sh" -exec chmod +x '{}' \;
