FROM python:3.8.0-alpine

WORKDIR /app
ADD requirements.txt /app

RUN pip3 install -r requirements.txt

ENTRYPOINT ["omnik-logger"]
CMD ["--help"]
