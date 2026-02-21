from crewclaw.tools.base import Tool
from typing import Any
import random

class WeatherTool(Tool):
    @property
    def name(self) -> str:
        return "get_current_weather"

    @property
    def description(self) -> str:
        return "Consulta a temperatura atual de uma cidade (Exemplo Simulado)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "O nome da cidade"
                }
            },
            "required": ["city"]
        }

    async def execute(self, city: str, **kwargs: Any) -> str:
        # Simulação de API de clima
        temp = random.randint(15, 35)
        conditions = random.choice(["Ensolarado", "Nublado", "Chuvoso"])
        return f"O clima atual em {city} é de {temp}°C, {conditions}."
