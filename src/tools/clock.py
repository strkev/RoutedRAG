from datetime import datetime
from langchain_core.tools import tool

@tool("get_current_time", description="Gibt das aktuelle Datum und die Uhrzeit zurück.")
def get_current_time() -> str:
    now = datetime.now()
    return now.strftime("Heute ist %A, der %d.%m.%Y und es ist %H:%M:%S Uhr.")