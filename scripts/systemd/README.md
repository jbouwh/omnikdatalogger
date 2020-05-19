# Service Configuration

> For `systemd` only!

Copy `omnikdatalogger.service` to `/lib/systemd/system/omnikdatalogger.service`

Next, enable and start service:

```
$ systemd enable omnikdatalogger
Created symlink /etc/systemd/system/multi-user.target.wants/omnikdatalogger.service → /lib/systemd/system/omnikdatalogger.service.
$ systemd start omnikdatalogger
```

Check if `omnikdatalogger.service` is running correctly:

```
$ systemd status omnikdatalogger
● omnikdatalogger.service - Omnik Data Logger service
   Loaded: loaded (/lib/systemd/system/omnikdatalogger.service; enabled; vendor preset: enabled)
   Active: active (running) since Tue 2019-06-18 06:55:08 UTC; 4min 36s ago
 Main PID: 2445 (python3)
    Tasks: 2 (limit: 4915)
   CGroup: /system.slice/omnikdatalogger.service
           └─2445 /usr/bin/python3 /usr/local/bin/omniklogger.py --config /etc/omnik/config.ini --interval 360
```