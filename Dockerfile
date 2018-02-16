FROM python:3.6-alpine3.7
MAINTAINER Sergey Levitin <slevitin@cryptology.com>

RUN addgroup -g 10001 app && adduser -u 10001 -D -h /app -G app app

COPY requirements.txt /app
WORKDIR /app

RUN set -x && \
    apk add --no-cache --update -t .build-deps build-base postgresql-dev gmp-dev libffi-dev linux-headers git && \
    python -m venv /venv && \
    /venv/bin/pip install --upgrade --no-cache-dir pip setuptools && \
    /venv/bin/pip install --no-cache-dir -r requirements.txt && \
    runDeps="$( \
      scanelf --needed --nobanner --recursive /venv \
        | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
        | sort -u \
        | xargs -r apk info --installed \
        | sort -u \
    )" && \
    apk add --no-cache -t .run-deps $runDeps && \
    apk del .build-deps

ENV PATH /venv/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

COPY . /app

RUN set -x \
    chmod -R a+rX /app && \
    python setup.py bdist_wheel && \
    pip install dist/transer_btc-0.1-py3-none-any.whl && \
    rm -rf dist build && \
    find . -name '__pycache__' -type d | xargs rm -rf && \
    python -c 'import compileall, os; compileall.compile_dir(os.curdir, force=1)' && \
    chown -R app:app /app

USER app
CMD ["python", "-u", "prod/runner.py"]

ARG APP_VERSION
ENV APP_VERSION ${APP_VERSION:-local_commit}
