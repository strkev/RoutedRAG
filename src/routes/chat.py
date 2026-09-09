import uuid
import json
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.schemas import Context, ChatMessageRequest, ChatRenameRequest
from src.agent import agent_instance, extract_token_usage
from src.models import evaluate_rules, SetupRequiredException, get_connection_config
from src.routes.settings import get_current_settings
from src.logger import logger
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
        raise HTTPException(status_code=404, detail="Chat nicht gefunden")
    return chat

@router.patch("/chats/{chat_id}")
async def rename_chat(chat_id: str, req: ChatRenameRequest):
    success = storage.rename_chat(chat_id, req.title)
    if not success:
        raise HTTPException(status_code=404, detail="Chat nicht gefunden")
    return {"status": "success", "title": req.title}

@router.delete("/chats/{chat_id}")
async def delete_chat(chat_id: str):
    success = storage.delete_chat(chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat nicht gefunden")
    return {"status": "success"}

def _resolve_routing(req: ChatMessageRequest, global_settings: dict):
    dynamic_model = req.dynamic_model if req.dynamic_model is not None else global_settings.get("dynamic_model_enabled", True)
    personality = req.personality or global_settings.get("active_personality", "default")
    custom_prompt = req.custom_prompt or global_settings.get("custom_prompt", "")

    if dynamic_model:
        routed_model, routed_conn = evaluate_rules(req.message)
        selected_model = routed_model
        selected_connection = routed_conn
        logger.info(f"Dynamisches Routing fuer '{req.message[:30]}': Modell='{selected_model}', Provider='{selected_connection}'")
    else:
        def_conn = get_connection_config(req.selected_connection)
        selected_model = req.selected_model or global_settings.get("default_model") or def_conn.get("default_model", "")
        selected_connection = req.selected_connection or def_conn.get("id", "")

    return dynamic_model, personality, custom_prompt, selected_model, selected_connection

@router.post("/chat")
async def send_chat_message(req: ChatMessageRequest):
    chat_id = req.chat_id or str(uuid.uuid4())
    global_settings = get_current_settings()

    dynamic_model, personality, custom_prompt, selected_model, selected_connection = _resolve_routing(req, global_settings)

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

        response = await agent_instance.ainvoke(
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
    except SetupRequiredException as se:
        error_msg = str(se)
        logger.warning(f"Setup erforderlich: {error_msg}")
        storage.save_message(chat_id, "assistant", error_msg, model_used="setup_required")
        return {
            "chat_id": chat_id,
            "role": "assistant",
            "content": error_msg,
            "model_used": "setup_required",
            "tool_calls": [],
            "token_usage": None
        }
    except Exception as e:
        error_msg = f"Fehler bei der Anfrage: {str(e)}"
        logger.error(f"Fehler in send_chat_message: {e}")
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

    dynamic_model, personality, custom_prompt, selected_model, selected_connection = _resolve_routing(req, global_settings)

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
        chosen_model = selected_model

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

            async for event in agent_instance.astream_events(
                {"messages": input_messages},
                config=config,
                context=ctx,
                version="v2"
            ):
                event_type = event.get("event")

                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk:
                        content = getattr(chunk, "content", "")
                        if isinstance(content, str) and content:
                            full_content += content
                            yield f"data: {json.dumps({'event': 'token', 'token': content})}\n\n"
                        elif isinstance(content, list):
                            for part in content:
                                if isinstance(part, str) and part:
                                    full_content += part
                                    yield f"data: {json.dumps({'event': 'token', 'token': part})}\n\n"
                                elif isinstance(part, dict) and part.get("type") == "text":
                                    txt = part.get("text", "")
                                    if txt:
                                        full_content += txt
                                        yield f"data: {json.dumps({'event': 'token', 'token': txt})}\n\n"

                elif event_type == "on_tool_start":
                    tool_info = {
                        "name": event.get("name", "tool"),
                        "args": event.get("data", {}).get("input", {})
                    }
                    tool_calls.append(tool_info)
                    yield f"data: {json.dumps({'event': 'tool_call', 'tool': tool_info})}\n\n"

            chosen_model = getattr(ctx, "selected_model", selected_model)
            final_state = agent_instance.get_state(config)
            token_usage = extract_token_usage(final_state.values) if (final_state and final_state.values) else {
                "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0
            }

            storage.save_message(
                chat_id,
                "assistant",
                full_content,
                model_used=chosen_model,
                tool_calls=tool_calls,
                token_usage=token_usage
            )

            yield f"data: {json.dumps({'event': 'done', 'model_used': chosen_model, 'chat_id': chat_id, 'token_usage': token_usage})}\n\n"

        except SetupRequiredException as se:
            err_msg = str(se)
            logger.warning(f"Streaming Setup erforderlich: {err_msg}")
            storage.save_message(chat_id, "assistant", err_msg, model_used="setup_required")
            yield f"data: {json.dumps({'event': 'error', 'error': err_msg})}\n\n"

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Fehler im Stream: {err_msg}")
            storage.save_message(chat_id, "assistant", f"Fehler: {err_msg}", model_used="error")
            yield f"data: {json.dumps({'event': 'error', 'error': err_msg})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
