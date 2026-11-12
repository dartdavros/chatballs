"""Translate Chatballs messages and model parameters into Responses input items."""

from __future__ import annotations

import json
from copy import deepcopy

from chatballs.ai.provider.base import ChatMessage, ProviderRejected, ToolSpec
from chatballs.ai.provider.openai_tools import NO_PARAMETERS
from chatballs.i18n import t


def input_items(messages: list[ChatMessage]) -> list[dict]:
    items = []
    for message in messages:
        if message.role == "tool":
            items.append({
                "type": "function_call_output", "call_id": message.tool_call_id,
                "output": message.content,
            })
        elif message.role == "assistant" and message.response_items:
            # Replay the entire output in order, including encrypted reasoning,
            # message phases and exact argument strings. Do not duplicate calls.
            items.extend(deepcopy(message.response_items))
        else:
            if message.content or not message.tool_calls:
                items.append({"role": message.role, "content": message.content})
            items.extend({
                "type": "function_call", "call_id": call.id, "name": call.name,
                "arguments": json.dumps(call.arguments, ensure_ascii=False),
            } for call in message.tool_calls)
    return items


def tools_payload(tools: list[ToolSpec]) -> list[dict]:
    return [{
        "type": "function", "name": tool.name, "description": tool.description,
        "parameters": deepcopy(tool.parameters or NO_PARAMETERS),
        # Existing HTTP/MCP schemas may have optional properties. Do not make
        # them required by implicitly opting into Responses strict mode.
        "strict": False,
    } for tool in tools]


def model_params(params: dict | None) -> dict:
    """Convert common Chat Completions options without mutating agent settings."""
    payload = deepcopy(params or {})
    # The tool loop owns history and execution mode. An unrelated stored
    # response/conversation must never be spliced into a tenant's request.
    for key in ("previous_response_id", "conversation", "stream", "background"):
        if payload.pop(key, None):
            raise ProviderRejected(t("ai.responses_unsupported_parameter", parameter=key))
    if payload.pop("n", 1) != 1:
        raise ProviderRejected(t("ai.responses_single_response"))
    for key in ("max_completion_tokens", "max_tokens"):
        value = payload.pop(key, None)
        if value is not None:
            payload.setdefault("max_output_tokens", value)
    effort = payload.pop("reasoning_effort", None)
    if effort is not None:
        reasoning = payload.setdefault("reasoning", {})
        if not isinstance(reasoning, dict):
            raise ProviderRejected(t("ai.responses_object_required", parameter="reasoning"))
        reasoning.setdefault("effort", effort)
    verbosity = payload.pop("verbosity", None)
    response_format = payload.pop("response_format", None)
    if verbosity is not None or response_format is not None:
        text = payload.setdefault("text", {})
        if not isinstance(text, dict):
            raise ProviderRejected(t("ai.responses_object_required", parameter="text"))
        if verbosity is not None:
            text.setdefault("verbosity", verbosity)
        if response_format is not None:
            if not isinstance(response_format, dict):
                raise ProviderRejected(t("ai.responses_object_required", parameter="response_format"))
            if response_format.get("type") == "json_schema":
                schema = response_format.get("json_schema")
                if not isinstance(schema, dict):
                    raise ProviderRejected(t("ai.responses_object_required", parameter="json_schema"))
                response_format = {**schema, "type": "json_schema"}
            text.setdefault("format", response_format)
    choice = payload.get("tool_choice")
    if isinstance(choice, dict) and choice.get("type") == "function" and "function" in choice:
        function = choice["function"]
        if not isinstance(function, dict) or not function.get("name"):
            raise ProviderRejected(t("ai.responses_function_name_required"))
        payload["tool_choice"] = {"type": "function", "name": function["name"]}
    return payload


def request_payload(*, messages: list[ChatMessage], model: str, params: dict | None,
                    tools: list[ToolSpec] | None) -> dict:
    payload = model_params(params)
    include = payload.get("include") or []
    if not isinstance(include, list) or not all(isinstance(item, str) for item in include):
        raise ProviderRejected(t("ai.responses_include_strings"))
    if "reasoning.encrypted_content" not in include:
        include.append("reasoning.encrypted_content")
    # These fields belong to the adapter, not the free-form model settings.
    for key in ("messages", "tools", "input", "model"):
        payload.pop(key, None)
    payload.update({
        "model": model, "input": input_items(messages), "include": include,
        "store": False, "stream": False, "background": False,
    })
    if tools:
        payload["tools"] = tools_payload(tools)
    return payload
