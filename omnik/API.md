# api.omnikportal.com


## user/account_validate
> Replace `USERNAME` and `PASSWORD`. The `appid` and `appkey` parameters represent the Android (~ and iOS?) application (hardcoded in source).

```
http -v POST https://api.omnikportal.com/v1/user/account_validate user_email==USERNAME user_password==PASSWORD user_type==1 uid:-1 appid:10038 appkey:Ox7yu3Eivicheinguth9ef9kohngo9oo 'Content-Type: application/x-www-form-urlencoded'

{
	"error_msg": "",
	"data": {
		"c_user_id": 104143,
		"user_type": "1",
		"plant_count": 1
	},
	"error_code": 0
}
```

## plant/list

```
http -v GET https://api.omnikportal.com/v1/plant/list uid:104143 appid:10038 appkey:Ox7yu3Eivicheinguth9ef9kohngo9oo

{
	"error_msg": "",
	"data": {
		"plants": [{
			"total_energy": "1046.60",
			"plant_id": 101563,
			"country": "Netherlands",
			"city": "Amsterdam",
			"timezone": "1",
			"image_url": "https://www.omnikportal.com/images/UserImages/Default.jpg",
			"latitude": "51.8835357",
			"line_status": "1",
			"peak_power": 5.28,
			"user_id": 104143,
			"alarm_status": "",
			"name": "John Doe",
			"eday": "0.70",
			"currency": "EUR",
			"create_date": "2019-05-02",
			"longitude": "4.2200928",
			"operator": "",
			"locale": "en-US",
			"income": "240.72",
			"current_power": 0.45,
			"today_energy": 0.7,
			"status": 1
		}],
		"count": 1
	},
	"error_code": 0
}
```

## /plant/data

```
http -v GET https://api.omnikportal.com/v1/plant/data plant_id==100893 uid:104143 appid:10038 appkey:Ox7yu3Eivicheinguth9ef9kohngo9oo 'Content-Type: application/x-www-form-urlencoded'

{
	"error_msg": "",
	"data": {
		"total_energy": "1046.60",
		"last_update_time": "2019-06-11T06:29:20Z",
		"peak_power_actual": 5.194,
		"timezone": "+01:00",
		"currency": "EUR",
		"today_energy": 0.7,
		"monthly_energy": 220.32,
		"yearly_energy": 903.14,
		"current_power": 0.45,
		"income": "240.72",
		"carbon_offset": 1.04,
		"efficiency": 4.17
	},
	"error_code": 0
}
```

===

The following URLs have been found:

```
AccessTokenUrl = "https://api.omnikportal.com/v1/user/account_validate";
AddDataLogger = "https://api.omnikportal.com/v1/device/datalogger/add";
AddPlantUrl = "https://api.omnikportal.com/v1/plant/add";
AreasUrl = "https://api.omnikportal.com/v1/plant/areas";
C_User_ListUrl = "https://api.omnikportal.com/v1/user/c_user_list";
DOWNLOAD = "https://play.google.com/store/apps/details?id=com.jialeinfo.omniksolar";
DataLoggerDeleteUrl = "https://api.omnikportal.com/v1/device/datalogger/delete";
DataLoggerListUrl = "https://api.omnikportal.com/v1/device/datalogger/list";
DataLoggerModifyUrl = "https://api.omnikportal.com/v1/device/datalogger/modify";
DataLoggerSimUrl = "https://api.omnikportal.com/v1/device/datalogger/sim";
DeletePlantUrl = "https://api.omnikportal.com/v1/plant/delete";
DeviceListUrl = "https://api.omnikportal.com/v1/device/list";
DtailsUrl = "https://api.omnikportal.com/v1/plant/details";
HistoryEnergyUrl = "https://api.omnikportal.com/v1/plant/energy";
InverterAlarmModifyUrl = "https://api.omnikportal.com/v1/device/inverter/alarm_modify";
InverterAlarmUrl = "https://api.omnikportal.com/v1/device/inverter/alarm";
InverterDataUrl = "https://api.omnikportal.com/v1/device/inverter/data";
ListUrl = "https://api.omnikportal.com/v1/plant/list";
ModifyPlantUrl = "https://api.omnikportal.com/v1/plant/modify";
ModifyUrl = "https://api.omnikportal.com/v1/user/c_user_list";
PlantDataUrl = "https://api.omnikportal.com/v1/plant/data";
RegisterUrl = "https://api.omnikportal.com/v1/user/b_user_register";
StatisticUrl = "https://api.omnikportal.com/v1/plant/statistic";
TodayPowerUrl = "https://api.omnikportal.com/v1/plant/power";
UsageUrl = "https://api.omnikportal.com/v1/user/account_validate";
VersionUrl = "https://api.omnikportal.com/v1/version/current";
eUrl = "https://api.omnikportal.com/v1";
userLogin = "https://api.omnikportal.com/v1/user/account_validate";
```
