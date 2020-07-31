# omnik-data-logger
> The `Docker` way
This directory contains all artefacts to run the `omnikdatalogger` as a `Docker` container.

If you wish, you can use the included `Makefile` to build and push the `Docker` image yourself.

```
$ make help
help                           This help.
build                          Build the Docker image. Use IMAGE_TAG to specify tag (default:latest)
push                           Tag and push to Docker Hub
login                          Login to Docker Hub
```

**PS**: this is already advanced use ... I already build and pushed the image to [Docker Hub](https://hub.docker.com/r/jbouwh/omnikdatalogger).

## Run

The following command will pull the `Docker` image, mount the `config.ini` and create the `Docker` container.

```
$ docker run --name omnikdatalogger -d -v ${PWD}/config.yaml:/config.yaml -p 10004:10004 --name omnikdatalogger jbouwh/omnikdatalogger:latest
```

If you want to access your P1 USB adapter for direct DSMR measurements you need to have acces to the USB port.
Add `--device=/dev/ttyUSB0` as option to the docker run command (assuming this is the correct USB device)

I also added a `docker-compose.yml` that can be used.  Run it at the folder where your `config.ini` file resites.

So, doing exactly the same ... but using `docker-compose`:

```
$ docker-compose -f /path/to/docker-compose.yml up -d
```

~ the end