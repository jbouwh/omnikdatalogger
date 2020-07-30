FROM python:3.8.0-alpine

WORKDIR /home/omnik
ADD requirements.txt /home/omnik

RUN pip3 install -r requirements.txt --upgrade && \
  adduser -D -u 1000 omnik

USER omnik

EXPOSE 10004

ENTRYPOINT ["omnikloggerproxy.py"]

CMD ["--config", "/config.ini"]