FROM bcgovimages/von-image:py36-1.15-1

ENV ENABLE_PTVSD 0

ADD requirements*.txt ./

RUN pip3 install --no-cache-dir \
    -r requirements.txt \
    -r requirements.askar.txt \
    -r requirements.bbs.txt \
    -r requirements.dev.txt

RUN mkdir aries_cloudagent && touch aries_cloudagent/__init__.py
ADD aries_cloudagent/version.py aries_cloudagent/version.py
ADD bin ./bin
ADD README.md ./
ADD setup.py ./

RUN pip3 install --no-cache-dir -e .

RUN mkdir logs && chown -R indy:indy logs && chmod -R ug+rw logs
ADD aries_cloudagent ./aries_cloudagent

ENTRYPOINT ["/bin/bash", "-c", "aca-py \"$@\"", "--"]
