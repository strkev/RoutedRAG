from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import Literal, Union

@dataclass
class Context:
    userId: str
    user_role: str = "yoda"

class WeatherResponse(BaseModel):
    summary: str = Field(description="A humorous weather summary")
    temperature_celsius: float = Field(description="Current temperature in Celsius")
    humidity: float = Field(description="Current relative humidity percentage")

class RoutingRule(BaseModel):
    id: str
    name: str
    target_model: str
    condition_type: Literal["role_equals", "contains_any", "min_length"]
    condition_value: Union[str, list[str], int]
    active: bool = True

class RoutingConfig(BaseModel):
    default_model: str
    rules: list[RoutingRule]