FROM python:3.8.0-alpine

WORKDIR /app
ADD requirements.txt /app

RUN pip3 install -r requirements.txt && \
  adduser -D -u 1000 omnik

USER omnik

ENTRYPOINT ["omnik-logger"]
CMD ["--help"]
