import httpx
from langchain.tools import tool

@tool("get_weather", description="Gibt aktuelle Wetterinformationen fuer einen beliebigen Stadtnamen zurueck (z.B. 'Frankfurt', 'Berlin', 'Tokyo').", return_direct=False)
def get_weather(city: str) -> dict:
    clean_city = city.strip()
    url = f"https://wttr.in/{clean_city}?format=j1"
    try:
        with httpx.Client(timeout=8.0) as client:
            response = client.get(url, headers={"User-Agent": "curl"})
            if response.status_code == 200:
                data = response.json()
                if "current_condition" in data and len(data["current_condition"]) > 0:
                    return data["current_condition"][0]
            return {"error": f"Wetterdienst antwortete mit Statuscode {response.status_code}"}
    except httpx.TimeoutException:
        return {"error": "Zeitueberschreitung bei der Wetterabfrage (Timeout nach 8 Sekunden)."}
    except Exception as e:
        return {"error": f"Fehler bei der Wetterabfrage: {str(e)}"}