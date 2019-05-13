# Use the offical nginx (based on debian)
FROM nginx:stable

# Required for HTTP Basic feature
RUN apt-get update -y && \
  apt-get install -y openssl ca-certificates && \
  rm -rf /var/lib/apt/lists/*

# Copy our OpenShift s2i scripts over to default location
COPY ./s2i/bin/ /usr/libexec/s2i/

# Expose this variable to OpenShift
LABEL io.openshift.s2i.scripts-url=image:///usr/libexec/s2i

# Copy config from source to container
COPY nginx.conf.template /tmp/

# Fix up permissions
RUN chmod -R 0777 /tmp /var /run /etc /mnt /usr/libexec/s2i/

# Work-around for issues with S2I builds on Windows
WORKDIR /tmp

# Nginx runs on port 8080 by default
EXPOSE 8080

# Switch to usermode
USER 104
