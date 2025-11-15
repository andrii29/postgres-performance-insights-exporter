ARG PYTHON_VERSION=3.14
ARG ALPINE_VERSION=3.22
FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION}

RUN apk add build-base libpq libpq-dev

COPY ./requirements.txt ./

RUN pip3 install --no-cache-dir -r ./requirements.txt

FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION}
ARG PYTHON_VERSION=3.14

RUN apk update \
    && apk upgrade \
    && apk add --no-cache libpq

ARG USER=app
ARG UID=1000

RUN adduser -D -s /bin/sh -u ${UID} ${USER}
WORKDIR /app

COPY --from=0 /usr/local/lib/python${PYTHON_VERSION}/site-packages/ /usr/local/lib/python${PYTHON_VERSION}/site-packages/
COPY . .
RUN chown -R ${USER}:${USER} /app
USER ${USER}
EXPOSE 9153

ENTRYPOINT ["python", "-u", "postgres-performance-insights-exporter.py"]
