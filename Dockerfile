FROM python:3.9.1-alpine3.12 as base

RUN apk add --update \
    tzdata

FROM python:3.9.1-alpine3.12

WORKDIR /home/omnik/source

COPY --from=base /usr/share/zoneinfo /usr/share/zoneinfo

ENV TZ=Europe/Amsterdam

COPY requirements.txt setup.py README.md ./
COPY apps/omnikdatalogger/. apps/omnikdatalogger/ 
COPY scripts/systemd/. scripts/systemd/ 

RUN pip3 install -r requirements.txt --upgrade && \
  adduser -D -u 1000 omnik && \
  python setup.py install

WORKDIR /home/omnik
USER omnik

EXPOSE 10004

ENTRYPOINT ["omniklogger.py"]

CMD ["--config", "/config.ini","--settings", "/config.yaml", "--persistant_cache_file", "/home/omnik/persistant_cache.json"]
