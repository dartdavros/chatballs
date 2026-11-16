"""Responses wire format and provider selection, with no live API calls."""

import json
from copy import deepcopy
from unittest import mock

from django.test import SimpleTestCase

from chatballs.ai.provider import openai_http, openai_responses, openai_tools
from chatballs.ai.provider.base import (
    ChatMessage,
    ProviderError,
    ProviderRejected,
    ToolCall,
    ToolSpec,
)
from chatballs.ai.provider.custom import CustomProvider
from chatballs.ai.provider.openai import OpenAIProvider
from chatballs.ai.provider.openrouter import OpenRouterProvider
from chatballs.ai.provider.responses_payload import input_items, model_params, request_payload
from chatballs.integrations.openai_urls import normalize_base_url, uses_responses

MODEL = "gpt-6.1-sol"
BASE = "https://api.openai.com/v1"
TOOL = ToolSpec("lookup", "Look up a record", {"type": "object", "properties": {"id": {"type": "string"}}})
REASONING = {"type": "reasoning", "id": "rs_test", "summary": [], "encrypted_content": "opaque-test-only"}
CALL = {"type": "function_call", "id": "fc_item", "call_id": "call_match", "name": "lookup",
        "arguments": '{"id": "42"}', "status": "completed"}
TEXT = {"type": "message", "id": "msg_test", "role": "assistant", "status": "completed",
        "phase": "final_answer", "content": [{"type": "output_text", "text": "Done", "annotations": []}]}


def response(*items):
    return {"id": "resp_test", "status": "completed", "model": MODEL,
            "output": deepcopy(list(items)), "usage": {"input_tokens": 12, "output_tokens": 8}}


def chat(provider, *, output=None, model=MODEL, **kwargs):
    with mock.patch.object(openai_http, "post_json", return_value=output or response(TEXT)) as post:
        result = provider.chat(messages=[ChatMessage("user", "Hello")], model=model, **kwargs)
    return result, post.call_args.kwargs


class ResponsesPayloadTests(SimpleTestCase):
    def test_flat_function_schema_and_stateless_defaults(self):
        params = {"store": True, "include": ["message.output_text.logprobs"], "tools": [{"type": "web_search"}]}
        original = deepcopy(params)
        payload = request_payload(messages=[ChatMessage("system", "Rules"), ChatMessage("user", "Hi")],
                                  model=MODEL, params=params, tools=[TOOL, ToolSpec("ping", "Ping")])
        self.assertEqual(payload["model"], MODEL)
        self.assertEqual(payload["input"], [{"role": "system", "content": "Rules"}, {"role": "user", "content": "Hi"}])
        self.assertNotIn("messages", payload)
        self.assertEqual(payload["tools"][0], {"type": "function", "name": "lookup", "description": "Look up a record",
                                             "parameters": TOOL.parameters, "strict": False})
        self.assertEqual(payload["tools"][1]["parameters"], {"type": "object", "properties": {}})
        self.assertFalse(payload["store"])
        self.assertFalse(payload["stream"])
        self.assertFalse(payload["background"])
        self.assertIn("reasoning.encrypted_content", payload["include"])
        self.assertEqual(params, original)

    def test_replay_preserves_reasoning_phases_arguments_and_order_without_duplicate_calls(self):
        result = openai_responses.parse_response(response(REASONING, CALL, TEXT), model=MODEL)
        messages = [ChatMessage("user", "Find 42"),
                    ChatMessage("assistant", result.text, tool_calls=result.tool_calls, response_items=result.response_items),
                    ChatMessage("tool", '{"found":true}', tool_call_id="call_match")]
        items = input_items(messages)
        self.assertEqual(items[1:4], [REASONING, CALL, TEXT])
        self.assertEqual(items[4], {"type": "function_call_output", "call_id": "call_match", "output": '{"found":true}'})
        self.assertEqual(sum(item.get("type") == "function_call" for item in items), 1)
        items[1]["encrypted_content"] = "changed"
        self.assertEqual(result.response_items[0]["encrypted_content"], "opaque-test-only")

    def test_message_history_without_native_items_and_no_tools(self):
        messages = [ChatMessage("assistant", "", tool_calls=(ToolCall("call_1", "ping", {}),)),
                    ChatMessage("tool", "ok", tool_call_id="call_1")]
        items = input_items(messages)
        self.assertEqual(items[0], {"type": "function_call", "call_id": "call_1", "name": "ping", "arguments": "{}"})
        payload = request_payload(messages=messages, model=MODEL, params=None, tools=None)
        self.assertNotIn("tools", payload)

    def test_common_parameters_are_translated_without_mutation(self):
        params = {"max_tokens": 128, "max_completion_tokens": 256, "reasoning_effort": "low", "verbosity": "high",
                  "tool_choice": {"type": "function", "function": {"name": "lookup"}},
                  "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "schema": {"type": "object"}, "strict": True}}}
        original = deepcopy(params)
        converted = model_params(params)
        self.assertEqual(converted["max_output_tokens"], 256)
        self.assertEqual(converted["reasoning"], {"effort": "low"})
        self.assertEqual(converted["text"]["verbosity"], "high")
        self.assertEqual(converted["text"]["format"], {"type": "json_schema", **params["response_format"]["json_schema"]})
        self.assertEqual(converted["tool_choice"], {"type": "function", "name": "lookup"})
        self.assertNotIn("max_tokens", converted)
        self.assertEqual(params, original)

    def test_native_parameters_take_precedence_and_none_tool_choice_survives(self):
        params = {"max_output_tokens": 512, "max_tokens": 128, "reasoning": {"effort": "high"},
                  "reasoning_effort": "low", "tool_choice": "none"}
        converted = model_params(params)
        self.assertEqual(converted["max_output_tokens"], 512)
        self.assertEqual(converted["reasoning"]["effort"], "high")
        self.assertEqual(converted["tool_choice"], "none")

    def test_unsupported_execution_modes_and_invalid_settings_are_rejected(self):
        for params in ({"stream": True}, {"background": True}, {"previous_response_id": "resp_other"},
                       {"conversation": "conv_other"}, {"n": 2}, {"reasoning": "bad", "reasoning_effort": "low"},
                       {"text": "bad", "verbosity": "high"}, {"response_format": "bad"},
                       {"response_format": {"type": "json_schema", "json_schema": []}},
                       {"tool_choice": {"type": "function", "function": {}}}, {"include": "bad"}):
            with self.subTest(params=params), self.assertRaises(ProviderRejected):
                request_payload(messages=[], model=MODEL, params=params, tools=None)


class ResponsesParsingTests(SimpleTestCase):
    def test_parses_text_and_usage_without_exposing_reasoning_in_repr(self):
        result = openai_responses.parse_response(response(REASONING, TEXT), model=MODEL)
        self.assertEqual((result.text, result.model, result.total_tokens), ("Done", MODEL, 20))
        self.assertNotIn("opaque-test-only", repr(result))
        self.assertNotIn("opaque-test-only", repr(ChatMessage("assistant", "", response_items=result.response_items)))

    def test_parses_multiple_calls_by_call_id_not_item_id(self):
        second = {**CALL, "id": "fc_second", "call_id": "call_second", "arguments": "{}"}
        result = openai_responses.parse_response(response(REASONING, CALL, second), model=MODEL)
        self.assertEqual([call.id for call in result.tool_calls], ["call_match", "call_second"])
        self.assertEqual(result.tool_calls[0].arguments, {"id": "42"})
        self.assertEqual(result.text, "")

    def test_refusal_is_a_textual_answer(self):
        refusal = {**TEXT, "content": [{"type": "refusal", "refusal": "Cannot do that"}]}
        self.assertEqual(openai_responses.parse_response(response(refusal), model=MODEL).text, "Cannot do that")

    def test_bad_or_incomplete_responses_are_errors_not_successful_tool_probes(self):
        invalid = [None, {}, response(), {**response(TEXT), "status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}},
                   {**response(TEXT), "status": "failed", "error": {"code": "server_error"}},
                   response({**CALL, "arguments": "not-json"}), response({**CALL, "arguments": "[]"}),
                   response({**CALL, "call_id": ""}), response(CALL, CALL),
                   response({**CALL, "status": "in_progress"}), {**response(TEXT), "output": None}]
        for data in invalid:
            with self.subTest(data=data), self.assertRaises(ProviderError):
                openai_responses.parse_response(data, model=MODEL)


class ResponsesProviderTests(SimpleTestCase):
    def test_native_openai_uses_responses_for_all_models_and_preserves_proxy(self):
        provider = OpenAIProvider(api_key="unit-test-not-a-real-key", proxy_url="http://proxy.test:8080", timeout=17)
        for model in (MODEL, "gpt-4.1"):
            _, sent = chat(provider, model=model)
            self.assertEqual((provider.name, sent["base_url"], sent["path"]), ("openai", BASE, "/responses"))
            self.assertEqual((sent["proxy_url"], sent["timeout"]), ("http://proxy.test:8080", 17))

    def test_custom_openai_gpt6_and_explicit_gateway_opt_in_use_responses(self):
        for base in (BASE, BASE + "/responses/", "https://gateway.test/v1/responses"):
            provider = CustomProvider(api_key="unit-test", base_url=base)
            _, sent = chat(provider)
            self.assertEqual(sent["path"], "/responses")
            self.assertEqual(sent["base_url"], normalize_base_url(base))

    def test_other_custom_servers_and_openrouter_keep_chat_completions(self):
        data = {"choices": [{"message": {"content": "legacy"}}]}
        for provider, model in ((CustomProvider(api_key="unit-test", base_url="https://gateway.test/v1"), MODEL),
                                (CustomProvider(api_key="unit-test", base_url=BASE), "gpt-4.1"),
                                (OpenRouterProvider(api_key="unit-test", base_url="https://openrouter.ai/api/v1"), "openai/" + MODEL)):
            result, sent = chat(provider, model=model, output=data)
            self.assertEqual(sent["path"], "/chat/completions")
            self.assertEqual(result.text, "legacy")

    def test_responses_capability_probe_uses_flat_tools_and_reasoning_budget(self):
        probe = {**CALL, "name": openai_tools.PROBE_TOOL.name, "arguments": "{}"}
        provider = OpenAIProvider(api_key="unit-test")
        with mock.patch.object(openai_http, "post_json", return_value=response(REASONING, probe)) as post:
            self.assertTrue(provider.supports_tools(model=MODEL))
        sent = post.call_args.kwargs
        self.assertEqual(sent["path"], "/responses")
        self.assertEqual(sent["payload"]["tool_choice"], {"type": "function", "name": openai_tools.PROBE_TOOL.name})
        self.assertEqual(sent["payload"]["reasoning"], {"effort": "low"})
        self.assertGreater(sent["payload"]["max_output_tokens"], 64)

    def test_incomplete_probe_is_unknown_not_cached_as_unsupported(self):
        provider = OpenAIProvider(api_key="unit-test")
        with mock.patch.object(openai_http, "post_json", return_value={**response(), "status": "incomplete"}), self.assertRaises(ProviderError):
            provider.supports_tools(model=MODEL)
        with mock.patch.object(openai_http, "post_json", return_value=response(TEXT)):
            self.assertFalse(provider.supports_tools(model=MODEL))

    def test_embedding_route_is_not_nested_below_responses(self):
        provider = OpenAIProvider(api_key="unit-test", base_url=BASE + "/responses")
        with mock.patch.object(openai_http, "post_json", return_value={"data": [{"embedding": [0.1]}]}) as post:
            provider.embed(texts=["hello"], model="text-embedding-3-small")
        self.assertEqual(post.call_args.kwargs["base_url"], BASE)
        self.assertEqual(post.call_args.kwargs["path"], "/embeddings")

    def test_http_transport_sends_bearer_json_and_normalized_responses_url(self):
        provider = OpenAIProvider(api_key="unit-test", base_url=BASE + "/responses", proxy_url="http://proxy.test:8080")
        with mock.patch.object(openai_http, "build_opener") as opener:
            opener.return_value.open.return_value.__enter__.return_value.read.return_value = json.dumps(response(TEXT)).encode()
            provider.chat(messages=[ChatMessage("user", "Привет")], model=MODEL)
        opener.assert_called_once_with("http://proxy.test:8080")
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual(request.full_url, BASE + "/responses")
        self.assertEqual(request.get_header("Authorization"), "Bearer unit-test")
        self.assertEqual(json.loads(request.data)["input"][0]["content"], "Привет")

    def test_url_normalization_and_explicit_protocol_selection(self):
        for suffix in ("", "/", "/responses", "/responses/", "/chat/completions/"):
            self.assertEqual(normalize_base_url(BASE + suffix), BASE)
        self.assertTrue(uses_responses(BASE, MODEL))
        self.assertTrue(uses_responses("https://gateway.test/v1/responses/", "any-model"))
        self.assertFalse(uses_responses("https://api.openai.com.attacker.test/v1", MODEL))
