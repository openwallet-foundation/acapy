FROM centos/nodejs-8-centos7

USER root

# Required in order to mount .npm as a volume to cache downloaded files
RUN mkdir .npm && \
  chown -R 1001:0 .npm && \
  chmod -R ug+rwx .npm

USER 1001
