"""Stateless Responses adapter using the existing HTTP/proxy/retry boundary."""

from __future__ import annotations

import json
from copy import deepcopy

from chatballs.ai.provider import openai_http
from chatballs.ai.provider.base import ChatMessage, ChatResult, ProviderError, ToolCall, ToolSpec
from chatballs.ai.provider.responses_payload import request_payload
from chatballs.i18n import t


def _string(value: object, label: str, *, nonempty: bool = False) -> str:
    if not isinstance(value, str) or (nonempty and not value):
        raise ValueError(f"invalid {label}")
    return value


def parse_response(data: dict, *, model: str) -> ChatResult:
    """Parse calls by call_id, never by the output item's separate fc_* id."""
    try:
        status = data.get("status")
        if status != "completed" or data.get("error"):
            # Never execute partial calls or silently report an empty success.
            # In particular an exhausted reasoning budget is NOT evidence that
            # the model lacks tool support (the probe caches only real answers).
            reason = data.get("error") or data.get("incomplete_details") or status
            raise ValueError(f"response not completed: {reason}")
        output = data["output"]
        if not isinstance(output, list):
            raise TypeError("response output is not a list")
        text = []
        calls = []
        for item in output:
            if not isinstance(item, dict):
                raise TypeError("response output item is not an object")
            if item.get("type") == "message":
                for part in item["content"]:
                    if part.get("type") == "output_text":
                        text.append(_string(part["text"], "output text"))
                    elif part.get("type") == "refusal":
                        text.append(_string(part["refusal"], "refusal"))
            elif item.get("type") == "function_call":
                if item.get("status") not in (None, "completed"):
                    raise ValueError("function call not completed")
                arguments = json.loads(item.get("arguments") or "{}")
                if not isinstance(arguments, dict):
                    raise TypeError("tool arguments are not an object")
                calls.append(ToolCall(
                    id=_string(item["call_id"], "call_id", nonempty=True),
                    name=_string(item["name"], "function name", nonempty=True),
                    arguments=arguments,
                ))
        if not any(text) and not calls:
            raise ValueError("response contains neither text nor function calls")
        if len({call.id for call in calls}) != len(calls):
            raise ValueError("duplicate function call_id")
        usage = data.get("usage") or {}
        return ChatResult(
            text="".join(text), model=data.get("model") or model,
            prompt_tokens=int(usage.get("input_tokens") or 0),
            completion_tokens=int(usage.get("output_tokens") or 0),
            tool_calls=tuple(calls), response_items=tuple(deepcopy(output)),
        )
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
        raise ProviderError(t("ai.unexpected_provider_response", error=error)) from error


def responses(*, base_url: str, api_key: str, messages: list[ChatMessage], model: str,
              timeout: float, proxy_url: str = "", params: dict | None = None,
              tools: list[ToolSpec] | None = None) -> ChatResult:
    payload = request_payload(messages=messages, model=model, params=params, tools=tools)
    data = openai_http.post_json(
        base_url=base_url, path="/responses", api_key=api_key, payload=payload,
        timeout=timeout, proxy_url=proxy_url,
    )
    return parse_response(data, model=model)
