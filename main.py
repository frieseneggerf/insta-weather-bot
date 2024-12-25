import os
import pyotp
from instagrapi.types import Location
from WeatherBot import WeatherBot
import json


def get_abs_path(path: str):
    return os.path.join(os.path.dirname(__file__), path)


with open(get_abs_path("weather_api_keys.json"), "r", encoding="utf-8") as file:
    api_keys = json.load(file)

with open(get_abs_path("bot_config.json"), "r", encoding="utf-8") as file:
    bot_config = json.load(file)

for config in bot_config["bots"]:
    bot = WeatherBot(api_keys, get_abs_path(config['path']), 2)
    totp_gen = pyotp.TOTP(config["totp_secret"])
    bot.init_client(config["username"], config["password"], totp_gen.now(),
                    get_abs_path(f"{config['path']}/settings.dump"))

    for city in config["cities"]:
        bot.add_city(city["name"], city["latlon"], city["position"], city["folding"], city["offset"])

    bot.get_water_data(config["water_url"])
    location = Location(lat=config["location"]["lat"], lng=config["location"]["lon"], name=config["location"]["name"])
    bot.make_post(location, config["pretty_name"], config["user_tag"])
