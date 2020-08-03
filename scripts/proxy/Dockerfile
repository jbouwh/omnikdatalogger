FROM python:3.8.0-alpine as base

RUN apk add --update \
    tzdata

FROM python:3.8.0-alpine

WORKDIR /home/omnik
ADD requirements.txt /home/omnik

COPY --from=base /usr/share/zoneinfo /usr/share/zoneinfo

ENV TZ=Europe/Amsterdam

RUN pip3 install -r requirements.txt --upgrade && \
  adduser -D -u 1000 omnik

USER omnik

EXPOSE 10004

ENTRYPOINT ["omnikloggerproxy.py"]

CMD ["--settings", "/config.yaml", "--config", "/config.ini"]
