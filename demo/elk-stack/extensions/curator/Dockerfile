FROM untergeek/curator:8.0.16@sha256:8ab15516eb320bddb042c6da3c81b57e4e69a7aac04efc32190db979fe0bfb5b

USER root

RUN >>/var/spool/cron/crontabs/nobody \
    echo '* * * * * /curator/curator /.curator/delete_log_files_curator.yml'

ENTRYPOINT ["crond"]
CMD ["-f", "-d8"]
