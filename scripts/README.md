# Service Configuration

> For `systemd` only!

Copy `omnik-data-logger.service` to `/lib/systemd/system/omnik-data-logger.service`

Next, enable and start service:

```
$ systemd enable omnik-data-logger
Created symlink /etc/systemd/system/multi-user.target.wants/omnik-data-logger.service → /lib/systemd/system/omnik-data-logger.service.
$ systemd start omnik-data-logger
```

Check if `omnik-data-logger.service` is running correctly:

```
$ systemd status omnik-data-logger
● omnik-data-logger.service - Omnik Data Logger service
   Loaded: loaded (/lib/systemd/system/omnik-data-logger.service; enabled; vendor preset: enabled)
   Active: active (running) since Tue 2019-06-18 06:55:08 UTC; 4min 36s ago
 Main PID: 2445 (python3)
    Tasks: 2 (limit: 4915)
   CGroup: /system.slice/omnik-data-logger.service
           └─2445 /usr/bin/python3 /usr/local/bin/omnik-logger --config /etc/omnik/config.ini --every 300
```