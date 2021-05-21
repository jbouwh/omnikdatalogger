# omnikdatalogger using docker

The following command will pull the `Docker` image, mount the `config.yaml` to `/config.yaml` in the container and create the `Docker` container.

```
$ docker run --name omnikdatalogger -d -v ${PWD}/config.yaml:/config.yaml -p 10004:10004 --name omnikdatalogger jbouwh/omnikdatalogger:latest
```

If you want to access your P1 USB adapter for direct DSMR measurements you need to have acces to the USB port.
Add `--device=/dev/ttyUSB0` as option to the docker run command (assuming this is the correct USB device)

If you wish you could use the home assistant config volume to store your configuration. You need root access to your host, or use portainer.
If you have root access, go to the folder: `/mnt/data/supervisor/homeassistant`.
Use the following command to create and start the container (omit the device part if you wish).
`docker run --name omnikdatalogger -d -v ${PWD}/omnikdatalogger.yaml:/config.yaml -p 10004:10004 --device=/dev/ttyUSB0 --restart unless-stopped --name omnikdatalogger jbouwh/omnikdatalogger:latest`

I also added a `docker-compose.yml` that can be used.  Run it at the folder where your `config.yaml` file resites.

So, doing exactly the same ... but using `docker-compose`:

```
$ docker-compose -f /path/to/docker-compose.yml up -d
```

> The `Dockerfile` can be found at the root of the repository. 