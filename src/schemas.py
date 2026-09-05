from dataclasses import dataclass
from pydantic import BaseModel, Field

@dataclass
class Context:
    userId: str
    user_role: str = "yoda"

class WeatherResponse(BaseModel):
    summary: str = Field(description="A humorous weather summary")
    temperature_celsius: float = Field(description="Current temperature in Celsius")
    humidity: float = Field(description="Current relative humidity percentage")