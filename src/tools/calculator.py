from langchain_core.tools import tool

@tool("calculator", description=" Calculates mathematical expressions like 12 * 45 or sqrt(144).", return_direct=False)
def calculate(expression: str) -> str:
    try:
        allowed_names = {"abs": abs, "round": round, "min": min, "max": max}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Ergebnis: {result}"
    except Exception as e:
        return f"Fehler bei der Berechnung: {str(e)}"