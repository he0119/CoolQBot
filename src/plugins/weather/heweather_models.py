from pydantic import BaseModel


class LocationItem(BaseModel):
    name: str
    id: str
    lat: str
    lon: str
    adm2: str
    adm1: str
    country: str
    tz: str
    utcOffset: str
    isDst: str
    type: str
    rank: str
    fxLink: str


class Refer(BaseModel):
    sources: list[str]
    license: list[str]


class LookupResp(BaseModel):
    """https://geoapi.qweather.com/v2/city/lookup"""

    code: str
    location: list[LocationItem] | None = None
    refer: Refer | None = None


class Now(BaseModel):
    obsTime: str
    temp: str
    feelsLike: str
    icon: str
    text: str
    wind360: str
    windDir: str
    windScale: str
    windSpeed: str
    humidity: str
    precip: str
    pressure: str
    vis: str
    cloud: str
    dew: str


class NowResp(BaseModel):
    """https://devapi.qweather.com/v7/weather/now"""

    code: str
    updateTime: str
    fxLink: str
    now: Now
    refer: Refer


class DailyItem(BaseModel):
    fxDate: str
    sunrise: str
    sunset: str
    moonrise: str
    moonset: str
    moonPhase: str
    moonPhaseIcon: str
    tempMax: str
    tempMin: str
    iconDay: str
    textDay: str
    iconNight: str
    textNight: str
    wind360Day: str
    windDirDay: str
    windScaleDay: str
    windSpeedDay: str
    wind360Night: str
    windDirNight: str
    windScaleNight: str
    windSpeedNight: str
    humidity: str
    precip: str
    pressure: str
    vis: str
    cloud: str
    uvIndex: str


class DailyResp(BaseModel):
    """https://devapi.qweather.com/v7/weather/3d"""

    code: str
    updateTime: str
    fxLink: str
    daily: list[DailyItem]
    refer: Refer
