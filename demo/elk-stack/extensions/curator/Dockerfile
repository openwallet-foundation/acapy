FROM untergeek/curator:8.0.21@sha256:eca135f7f6e1781cfbca9e7cb3fa8237a481cfd815aa7ef52b38adb268ab6f97

USER root

RUN >>/var/spool/cron/crontabs/nobody \
    echo '* * * * * /curator/curator /.curator/delete_log_files_curator.yml'

ENTRYPOINT ["crond"]
CMD ["-f", "-d8"]
