from langchain.agents.middleware import ModelRequest, dynamic_prompt

@dynamic_prompt
def user_role_prompt(request: ModelRequest) -> str:
    user_role = getattr(request.runtime.context, "user_role", "default")
    base_prompt = "You are a helpful and very concise assistant."

    match user_role:
        case "expert":
            return f"{base_prompt} Provide detailed technical responses."
        case "funny":
            return f"{base_prompt} Always make jokes and be humorous while remaining helpful."
        case "yoda":
            return f"{base_prompt} Explain everything as if you were Yoda, you must."
        case _:
            return base_prompt