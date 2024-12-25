import datetime
import os
from pathlib import Path
from typing import Dict, Tuple
import requests
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup as Bs
from instagrapi import Client
from instagrapi.types import Location
import instagrapi.exceptions
from babel.dates import format_date


class WeatherBot:
    def log(self, message: str) -> None:
        print(message)
        with open(self.__get_abs_path("log.txt"), "a", encoding="utf-8") as log_file:
            log_file.write(f"[{datetime.datetime.now()}] {message}\n")

    def __get_abs_path(self, path: str) -> str:
        return os.path.join(self.path, path)

    def __init__(self, api_keys: Dict, path: str, days: int) -> None:
        self.keys = api_keys
        self.path = path
        self.days = days
        self.cities = {}
        self.w_temp = "None"
        self.w_time = ""
        self.client = None

    def init_client(self, username: str, password: str, totp: str, data_dump_path: str, country: str = "DE",
                    c_code: int = 49, locale: str = "de_DE", utc_offset: int = 1) -> bool:
        """
        Log the client in and get a session from instagram
        :param username: Username of the bot instagram account
        :param password: Password of the bot instagram account
        :param totp: 6 digit TOTP for the 2nd factor authentication to the bot instagram account
        :param data_dump_path: Location of the session dump
        :param country: Country for the session (e.g. "DE")
        :param c_code: Tel country code for the session (e.g. 49)
        :param locale:  Locale for the session (e.g. "de_DE")
        :param utc_offset: UTC offset in hours for the session (e.g. 1)
        :return: True if successful
        """
        self.log("Login " + username)
        for attempt in range(2):
            client = Client()
            client.set_country(country)
            client.set_locale(locale)
            client.set_country_code(c_code)
            client.set_timezone_offset(utc_offset * 3600)
            if os.path.exists(data_dump_path):
                client.load_settings(Path(data_dump_path))
            client.login(username, password, verification_code=totp)
            try:
                client.get_timeline_feed()
                self.log("Login successful")
                self.client = client
                client.dump_settings(Path(data_dump_path))
                return True
            except instagrapi.exceptions.LoginRequired as e:
                self.log("[Error] " + e.message)
                return False

    def get_water_data(self, url_snippet: str) -> bool:
        r = requests.get(
            f"https://www.gkd.bayern.de/de/seen/wassertemperatur/isar/{url_snippet}/messwerte/tabelle").text
        soup = Bs(r, features="html.parser")
        table = soup.find("tbody").find_all("tr")
        try:
            self.w_time = table[0].find_all("td")[0].text[11:16]
            self.w_temp = table[0].find_all("td")[1].text
        except Exception as e:
            for a in e.args:
                self.log(a)
        if self.w_temp is None:
            self.log("[Error] Could not retrieve water temperature, proceeding without")
            return False
        else:
            self.log("Water temperature retrieved")
            return True

    def add_city(self, name: str, coords: str, position: Tuple[int, int], folding: str, offset: Tuple[int, int]) \
            -> bool:
        """
        Add a city with corresponding data to the bot and get weather data for it
        :param name: Name of the city
        :param coords: Coordinates of the city ("latitude,longitude")
        :param position: Position in pixels where the city is located on the image
        :param folding: Wether the text box should fold to the left "l" or right "r" of the city marker
        :param offset: Offset in pixels applied to the text box
        :return: True if successful
        """
        self.log(f"Adding {name}")
        self.cities[name] = {
            "coords": coords,
            "position": position,
            "folding": folding,
            "offset": offset,
            "weather": []
        }

        try:
            q = f"https://api.weatherapi.com/v1/forecast.json?key={self.keys['wapi']}&days={self.days}&aqi=no&alerts" \
                f"=no&lang=de&q=" + coords
            r = requests.get(q).json()
            for i in range(self.days):
                weather = {
                    "mintemp_c": str(r["forecast"]["forecastday"][i]["day"]["mintemp_c"]).replace(".", ","),
                    "maxtemp_c": str(r["forecast"]["forecastday"][i]["day"]["maxtemp_c"]).replace(".", ","),
                    "condition": r["forecast"]["forecastday"][i]["day"]["condition"]["text"],
                }
                self.cities[name]["weather"].append(weather)
            return True
        except Exception as e:
            self.log("[Error] Weather provider weatherapi.com failed, using secondary provider")
            for a in e.args:
                self.log(a)
            try:
                self.cities[name]["weather"] = []
                q = f"https://api.openweathermap.org/data/2.5/onecall?lang=de&units=metric&exclude=current,minutely," \
                    f"hourly,alerts&lat={coords.split(',')[0]}&lon={coords.split(',')[1]}&appid={self.keys['owmap']}"
                r = requests.get(q).json()
                for i in range(self.days):
                    weather = {
                        "mintemp_c": str(round(r["daily"][i]["temp"]["min"], 1)).replace(".", ","),
                        "maxtemp_c": str(round(r["daily"][i]["temp"]["max"], 1)).replace(".", ","),
                        "condition": r["daily"][i]["weather"][0]["description"],
                    }
                    self.cities[name]["weather"].append(weather)
                return True
            except Exception as e:
                self.log(f"[Error] Weather provider openweathermap.org failed, could not add {name}")
                for a in e.args:
                    self.log(a)
                return False

    def __draw_city(self, city: str, draw: ImageDraw, day: int) -> None:
        """
        Place marker and text for a city on the image
        :param city: Name of the city from self.cities to be added
        :param draw: The ImageDraw to add to
        :param day: Day of set to be included (e.g. 0, 1, ...)
        """
        origin = self.cities[city]["position"]
        folding = self.cities[city]["folding"]
        offset = self.cities[city]["offset"]
        weather = self.cities[city]["weather"][day]
        # config
        dim = (350, 210)
        marker_rad = 15
        arrow_height = 50
        padding = 15
        city_font = ImageFont.truetype(self.__get_abs_path("../fonts/PlexusSans-SemiBold.otf"), 60)
        temp_font = ImageFont.truetype(self.__get_abs_path("../fonts/PlexusSans-Regular.otf"), 45)
        cond_font = ImageFont.truetype(self.__get_abs_path("../fonts/PlexusSans-Regular.otf"), 40)
        # make sure pane is wide enough
        temp_str = (weather["mintemp_c"] + " bis " + weather["maxtemp_c"]) + "°C"
        temp_size = draw.textlength(temp_str, font=temp_font) + 2 * padding
        cond_size = draw.textlength(weather["condition"], font=cond_font) + 2 * padding
        if temp_size > cond_size:
            min_size = temp_size
        else:
            min_size = cond_size

        if min_size > dim[0]:
            dim = (min_size, dim[1])

        # draw objects
        if folding == "r":
            corner = (origin[0] + offset[0], origin[1] + offset[1])
        else:
            corner = (origin[0] - dim[0] + offset[0], origin[1] + offset[1])

        draw.rounded_rectangle((corner[0], corner[1], corner[0] + dim[0], corner[1] + dim[1]), 10, (244, 244, 244))
        draw.polygon((origin[0], origin[1], origin[0] + offset[0], origin[1] + arrow_height / 2, origin[0] + offset[0],
                      origin[1] - arrow_height / 2), (244, 244, 244))
        draw.ellipse((origin[0] - marker_rad, origin[1] - marker_rad, origin[0] + marker_rad, origin[1] + marker_rad),
                     (238, 125, 0))

        # draw texts
        draw.text((corner[0] + padding, corner[1] + padding), city, (0, 0, 0), font=city_font)
        draw.text((corner[0] + padding, corner[1] + padding + city_font.size + 5), temp_str, (0, 0, 0),
                  font=temp_font)
        draw.text((corner[0] + padding, corner[1] + padding + city_font.size + temp_font.size + 15),
                  weather["condition"], (0, 0, 0), font=cond_font)

    def __create_image(self, day: int, w_temp: str, title: str, watermark: str) -> Image:
        """
        Create an image with the supplied data
        :param day: Day of set to be included (e.g. 0, 1, ...)
        :param w_temp: Water temperature (e.g. "5,6")
        :param title: Title text at top of post (e.g. "Wetter am See")
        :param watermark: User tag at bottom of post (e.g. "@Wetter.am.See")
        :return: Image object
        """
        img = Image.open(self.__get_abs_path("post_template.png"))
        draw = ImageDraw.Draw(img)
        date = datetime.date.today() + datetime.timedelta(days=day)

        # add title/date
        title_text = title
        title_font = ImageFont.truetype(self.__get_abs_path("../fonts/Gidole-Regular.ttf"), 200)
        title_with = draw.textlength(title_text, title_font)
        draw.rectangle((40, 40, 80 + title_with, 240), (255, 255, 255))
        draw.text((60, 30), title_text, (0, 0, 0), font=title_font)

        date_text = format_date(date, format="full", locale="de_DE")
        date_font = ImageFont.truetype(self.__get_abs_path("../fonts/Gidole-Regular.ttf"), 100)
        date_with = draw.textlength(date_text, date_font)
        draw.rectangle((40, 260, 80 + date_with, 385), (255, 255, 255))
        draw.text((60, 260), date_text, (0, 0, 0), font=date_font)

        # draw info panes
        for city in self.cities.keys():
            self.__draw_city(city, draw, day)

        if w_temp != "None":
            draw.rounded_rectangle((1500, 1900, 1500 + 480, 1900 + 150), 10, (224, 224, 224))
            city_font = ImageFont.truetype(self.__get_abs_path("../fonts/PlexusSans-SemiBold.otf"), 50)
            draw.text((1500 + 10, 1900 + 10), "Wassertemperatur:", (0, 0, 0), font=city_font)

            weather_font = ImageFont.truetype(self.__get_abs_path("../fonts/PlexusSans-Regular.otf"), 50)
            draw.text((1500 + 240 - draw.textlength(w_temp + "°C", font=weather_font) / 2, 1900 + 70), w_temp + "°C",
                      (0, 0, 0),
                      font=weather_font)

        label_font = ImageFont.truetype(self.__get_abs_path("../fonts/Gidole-Regular.ttf"), 60)
        draw.text((40, 2100), watermark, (80, 80, 80), font=label_font)

        return img

    def make_post(self, location: Location, title: str, watermark: str) -> bool:
        """
        Generate and post an image set
        :param location: instagrapi.types.Location object to be attached to the post
        :param title: Title text at top of post (e.g. "Wetter am See")
        :param watermark: User tag at bottom of post (e.g. "@Wetter.am.See")
        :return: True if successful
        """
        if not self.client:
            self.log("[Error] Client not initialized")
            return False
        paths = []
        for i in range(self.days):
            self.log(f"Creating image {i + 1}/{self.days}")
            paths.append(Path(self.__get_abs_path(f"latest_post/{i}.jpg")))
            if i == 0:
                self.__create_image(i, self.w_temp, title, watermark).convert("RGB").save(paths[i])
            else:
                self.__create_image(i, "None", title, watermark).convert("RGB").save(paths[i])

        self.log("Processing caption")
        with open(self.__get_abs_path("caption.txt"), "r", encoding='utf-8') as caption_file:
            raw_caption = caption_file.read()
        caption_text = raw_caption.replace("w_time", f"({self.w_time})")

        self.log("Uploading post")
        try:
            self.client.album_upload(paths, caption_text, location=location)
            self.log("Upload successful")
            return True
        except Exception as e:
            self.log("[Error] Upload failed")
            for a in e.args:
                self.log(a)
            return False
