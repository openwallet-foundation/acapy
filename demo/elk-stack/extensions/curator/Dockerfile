FROM untergeek/curator:9.0.0@sha256:1cd770aeec076ef1b5d3768b4213e50654f3c0e1aecaec46d6c9150a0c8d2a61

USER root

RUN >>/var/spool/cron/crontabs/nobody \
    echo '* * * * * /curator/curator /.curator/delete_log_files_curator.yml'

ENTRYPOINT ["crond"]
CMD ["-f", "-d8"]
