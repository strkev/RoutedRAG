import requests
from langchain.tools import tool

@tool("get_weather", description="Return current weather information for any city name (e.g. 'Frankfurt', 'Berlin', 'Tokyo')", return_direct=False)
def get_weather(city: str) -> dict:
    url = f"https://wttr.in/{city.strip()}?format=j1"
    response = requests.get(url, headers={"User-Agent": "curl"})
    return response.json()["current_condition"][0]