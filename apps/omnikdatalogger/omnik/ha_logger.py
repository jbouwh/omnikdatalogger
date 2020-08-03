import datetime


class hybridlogger:

    @staticmethod
    def ha_log(logger, hass_api, level, message):
        if hass_api and hasattr(hass_api, 'log'):
            hass_api.log(message, level=level)
        else:
            if level == "DEBUG":
                logger.debug(f"@ {datetime.datetime.now().isoformat()} {message}")
            elif level == "INFO":
                logger.info(f"I {datetime.datetime.now().isoformat()} {message}")
            elif level == "WARNING":
                logger.warning(f"W {datetime.datetime.now().isoformat()} {message}")
            elif level == "ERROR":
                logger.error(f"E {datetime.datetime.now().isoformat()} {message}")
