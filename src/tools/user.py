from langchain.tools import tool, ToolRuntime
from src.schemas import Context

@tool("locate_user", description="Lookup a user's location and coordinates based on context", return_direct=False)
def locate_user(runtime: ToolRuntime[Context]) -> dict:
    match runtime.context.userId:
        case "ABCD123":
            return {"city": "Oberursel", "lat": 50.20, "lon": 8.58}
        case "XYZ456":
            return {"city": "London", "lat": 51.50, "lon": -0.12}
        case _:
            return {"city": "Unknown", "lat": 0.0, "lon": 0.0}