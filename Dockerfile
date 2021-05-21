FROM python:3.9.1-alpine3.12 as base

RUN apk add --update \
    tzdata

FROM python:3.9.1-alpine3.12

WORKDIR /source

COPY --from=base /usr/share/zoneinfo /usr/share/zoneinfo

ENV TZ=Europe/Amsterdam

COPY requirements.txt setup.py README.md ./
COPY scripts/systemd/. scripts/systemd/ 
COPY apps/omnikdatalogger/. apps/omnikdatalogger/ 

RUN pip3 install -r requirements.txt --upgrade && \
  python setup.py install && \
  adduser -D -u 1000 omnik && \
  mkdir /config && \
  cp -u /source/apps/omnikdatalogger/data_fields.json /config && \
  chown omnik.users -R /config

WORKDIR /config
USER omnik

EXPOSE 10004

ENTRYPOINT ["omniklogger.py"]

CMD ["--config", "/config/config.ini","--settings", "/config/config.yaml", "--persistant_cache_file", "/config/persistant_cache.json", "--data_config /config/data_fields.json"]
