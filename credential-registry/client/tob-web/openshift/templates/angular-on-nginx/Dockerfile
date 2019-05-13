# Get community edition of nodejs v6.x
FROM angular-app:latest as builder
FROM nginx-runtime:latest

# Copy the build artifacts from the 'builder' image
# to the distribution folder on the runtime image.
COPY --from=builder /opt/app-root/src/dist/. /tmp/app/dist/

# Since the runtime image is itself an s2i image we need to
# short circuit the s2i lifecycle.
# The runtime image "loses" its s2i runtime voodoo when it
# is used in a dockerSrategy, which is why the explicit `CMD` is necessary
CMD  /usr/libexec/s2i/run
