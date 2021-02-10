FROM python:3.9.1-alpine as base

RUN apk add --update \
    tzdata

FROM python:3.9.1-alpine

WORKDIR /home/omnik

ADD requirements.txt /home/omnik

COPY --from=base /usr/share/zoneinfo /usr/share/zoneinfo

ENV TZ=Europe/Amsterdam

RUN pip3 install -r requirements.txt --upgrade && \
  adduser -D -u 1000 omnik

USER omnik

EXPOSE 10004

ENTRYPOINT ["omniklogger.py"]

CMD ["--config", "/config.ini","--settings", "/config.yaml", "--persistant_cache_file", "/home/omnik/persistant_cache.json"]
