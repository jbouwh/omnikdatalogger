# api.omnikportal.com


## user/account_validate
> Replace `USERNAME` and `PASSWORD`. The `appid` and `appkey` parameter seem to represent the Web UI as a trusted application.

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
