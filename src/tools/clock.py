from datetime import datetime
from langchain_core.tools import tool

@tool("get_current_time", description="Returns the current Date and Time.", return_direct=False)
def get_current_time() -> str:
    now = datetime.now()
    return now.strftime("Today is %A, the %d.%m.%Y and %H:%M:%S O Clock.")