
# Instagram Weather Bot

[![Static Badge](https://img.shields.io/badge/Blog_Post-blue)](https://friesenegger.xyz/projects/insta-weather-bot/)

A python project to run a bot that posts weather forecast and water temperature for a defined lake.

This is a project I did to learn about web scraping, api usage and image manipulation in python.

The example bots post about [Lake Starnberg](https://www.instagram.com/wetter.am.see/) and [Ammersee](https://www.instagram.com/wetter.am.ammersee/) in Bavaria, Germany.




## Installation/Usage

1. Clone the repo and setup and activate a venv according to requirements.txt
2. Obtain API keys for weatherapi.com and openweathermap.org (fallback) and store them in `weather_api_keys.json`
3. Create a png with the background for your posts (look at examples, note pixel coordinates of cities to be added) and store it in a subfolder for your bot
4. Provide a `caption.txt` in the folder for your bot containing a caption for the post
5. Configure your bot in `bot_config.json` (remove example entries from config)
6. Modify the `WeatherBot.get_water_data()` function to retrieve water temp for your lake (or remove the feature) as this function only works with Waterscience Service Bavaria
7. run `main.py`
8. Setup a cronjob if you want to run it on a schedule
