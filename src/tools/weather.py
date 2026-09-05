import requests
from langchain.tools import tool

@tool("get_weather", description="Return weather information for latitude and longitude", return_direct=False)
def get_weather(lat: float, lon: float) -> dict:
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m"
    )
    response = requests.get(url)
    return response.json()