import uuid
import json
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.schemas import Context, ChatMessageRequest, ChatRenameRequest
from src.agent import agent_instance, extract_token_usage
from src.models import evaluate_rules
from src.routes.settings import get_current_settings
import src.chat_storage as storage

router = APIRouter(prefix="/api", tags=["chat"])

@router.get("/chats")
async def list_chats(limit: int = 10, offset: int = 0):
    return storage.list_chats(limit=limit, offset=offset)

@router.post("/chats")
async def create_chat(req: dict = None):
    chat_id = str(uuid.uuid4())
    title = (req or {}).get("title", "Neuer Chat")
    personality = (req or {}).get("personality", "default")
    dynamic_model = (req or {}).get("dynamic_model", True)
    return storage.create_chat(chat_id, title=title, personality=personality, dynamic_model=dynamic_model)

@router.get("/chats/{chat_id}")
async def get_chat(chat_id: str):
    chat = storage.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.patch("/chats/{chat_id}")
async def rename_chat(chat_id: str, req: ChatRenameRequest):
    success = storage.rename_chat(chat_id, req.title)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "success", "title": req.title}

@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
    success = storage.delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": "success"}

@router.post("/chat")
async def send_chat_message(req: ChatMessageRequest):
    chat_id = req.chat_id or str(uuid.uuid4())
    global_settings = get_current_settings()
    
    dynamic_model = req.dynamic_model if req.dynamic_model is not None else global_settings.get("dynamic_model_enabled", True)
    personality = req.personality or global_settings.get("active_personality", "default")
    custom_prompt = req.custom_prompt or global_settings.get("custom_prompt", "")
    
    if dynamic_model:
        routed_model, routed_conn = evaluate_rules(req.message)
        selected_model = routed_model
        selected_connection = routed_conn
        print(f"[Chat] Dynamisch geroutet für '{req.message[:35]}': Modell='{selected_model}', Provider='{selected_connection}'")
    else:
        selected_model = req.selected_model or global_settings.get("default_model", "google/gemma-4-31b-it")
        selected_connection = getattr(req, "selected_connection", None) or "uni"
    
    # Save user message to database
    storage.save_message(
        chat_id=chat_id,
        role="user",
        content=req.message,
        personality=personality,
        dynamic_model=dynamic_model
    )

    ctx = Context(
        user_role=personality,
        dynamic_model=dynamic_model,
        selected_model=selected_model,
        selected_connection=selected_connection,
        user_message=req.message,
        custom_prompt=custom_prompt
    )
    config = {"configurable": {"thread_id": chat_id}}
    
    try:
        state = agent_instance.get_state(config)
        if not state.values or not state.values.get("messages"):
            existing_chat = storage.get_chat(chat_id)
            history = []
            if existing_chat and existing_chat.get("messages"):
                for m in existing_chat["messages"][:-1]:
                    history.append({"role": m["role"], "content": m["content"]})
            input_messages = history + [{"role": "user", "content": req.message}]
        else:
            input_messages = [{"role": "user", "content": req.message}]

        response = agent_instance.invoke(
            {"messages": input_messages},
            config=config,
            context=ctx,
        )
        
        last_msg = response["messages"][-1]
        final_content = str(last_msg.content)
        chosen_model = getattr(ctx, "selected_model", selected_model)
        
        tool_calls = []
        for msg in response["messages"]:
            if getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "name": tc.get("name"),
                        "args": tc.get("args")
                    })

        token_usage = extract_token_usage(response)

        storage.save_message(
            chat_id, 
            "assistant", 
            final_content, 
            model_used=chosen_model, 
            tool_calls=tool_calls,
            token_usage=token_usage
        )

        return {
            "chat_id": chat_id,
            "role": "assistant",
            "content": final_content,
            "model_used": chosen_model,
            "tool_calls": tool_calls,
            "token_usage": token_usage
        }
    except Exception as e:
        error_msg = f"Fehler bei der Anfrage: {str(e)}"
        storage.save_message(chat_id, "assistant", error_msg, model_used="error")
        return {
            "chat_id": chat_id,
            "role": "assistant",
            "content": error_msg,
            "model_used": "error",
            "tool_calls": [],
            "token_usage": None
        }

@router.post("/chat/stream")
async def stream_chat_message(req: ChatMessageRequest):
    chat_id = req.chat_id or str(uuid.uuid4())
    global_settings = get_current_settings()

    dynamic_model = req.dynamic_model if req.dynamic_model is not None else global_settings.get("dynamic_model_enabled", True)
    personality = req.personality or global_settings.get("active_personality", "default")
    custom_prompt = req.custom_prompt or global_settings.get("custom_prompt", "")

    if dynamic_model:
        routed_model, routed_conn = evaluate_rules(req.message)
        selected_model = routed_model
        selected_connection = routed_conn
        print(f"[Chat-Stream] Dynamisch geroutet für '{req.message[:35]}': Modell='{selected_model}', Provider='{selected_connection}'")
    else:
        selected_model = req.selected_model or global_settings.get("default_model", "google/gemma-4-31b-it")
        selected_connection = getattr(req, "selected_connection", None) or "uni"

    # Save user message immediately before streaming begins
    storage.save_message(
        chat_id=chat_id,
        role="user",
        content=req.message,
        personality=personality,
        dynamic_model=dynamic_model
    )

    ctx = Context(
        user_role=personality,
        dynamic_model=dynamic_model,
        selected_model=selected_model,
        selected_connection=selected_connection,
        user_message=req.message,
        custom_prompt=custom_prompt
    )
    config = {"configurable": {"thread_id": chat_id}}

    async def event_generator() -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'event': 'init', 'chat_id': chat_id})}\n\n"
        
        full_content = ""
        tool_calls = []
        try:
            state = agent_instance.get_state(config)
            if not state.values or not state.values.get("messages"):
                existing_chat = storage.get_chat(chat_id)
                history = []
                if existing_chat and existing_chat.get("messages"):
                    for m in existing_chat["messages"][:-1]:
                        history.append({"role": m["role"], "content": m["content"]})
                input_messages = history + [{"role": "user", "content": req.message}]
            else:
                input_messages = [{"role": "user", "content": req.message}]

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: agent_instance.invoke(
                    {"messages": input_messages},
                    config=config,
                    context=ctx
                )
            )

            last_msg = response["messages"][-1]
            full_content = str(last_msg.content)
            chosen_model = getattr(ctx, "selected_model", selected_model)

            for msg in response["messages"]:
                if getattr(msg, "tool_calls", None):
                    for tc in msg.tool_calls:
                        tool_info = {"name": tc.get("name"), "args": tc.get("args")}
                        tool_calls.append(tool_info)
                        yield f"data: {json.dumps({'event': 'tool_call', 'tool': tool_info})}\n\n"

            chunk_size = 8
            for i in range(0, len(full_content), chunk_size):
                chunk = full_content[i:i + chunk_size]
                yield f"data: {json.dumps({'event': 'token', 'token': chunk})}\n\n"
                await asyncio.sleep(0.015)

            token_usage = extract_token_usage(response)

            storage.save_message(
                chat_id, 
                "assistant", 
                full_content, 
                model_used=chosen_model, 
                tool_calls=tool_calls,
                token_usage=token_usage
            )

            yield f"data: {json.dumps({'event': 'done', 'model_used': chosen_model, 'chat_id': chat_id, 'token_usage': token_usage})}\n\n"
        except Exception as e:
            err = str(e)
            storage.save_message(chat_id, "assistant", f"Fehler: {err}", model_used="error")
            yield f"data: {json.dumps({'event': 'error', 'error': err})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
