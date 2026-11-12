"""Round-trip Responses items through the real tool/skill loop."""

import json
from dataclasses import replace
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase

from chatballs.ai.diagnostic_capture import chat_payload, request_payload
from chatballs.ai.invocation_jobs import ChatJob
from chatballs.ai.provider import openai_http, openai_responses
from chatballs.ai.provider.base import ChatMessage
from chatballs.ai.provider.openai import OpenAIProvider
from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.ai.test_openai_responses import CALL, MODEL, REASONING, TEXT, TOOL, response
from chatballs.ai.tool_loop import MAX_TOOL_ROUNDS, run_tool_loop, with_tools
from chatballs.ai.turn_skills import LOAD_SKILL, TurnSkill, TurnSkills


def dispatch(job):
    return job.provider.chat(messages=job.messages, model=job.model, params=job.params, tools=job.tools)


class ResponsesLoopTests(SimpleTestCase):
    def setUp(self):
        self.skills = TurnSkills((TurnSkill("skill-1", "Clarify", "Missing reference", "Ask for the reference"),))
        self.mask = Pseudonymizer()
        self.job = ChatJob(OpenAIProvider(api_key="unit-test"), MODEL, [ChatMessage("user", "Help")], (0, 0), 0)

    def test_skill_loading_and_consecutive_calls_keep_full_reasoning_context(self):
        calls = [{**CALL, "id": f"fc_{number}", "call_id": f"call_{number}", "name": LOAD_SKILL,
                  "arguments": '{"skill_id": "skill-1"}'} for number in range(2)]
        reasonings = [{**REASONING, "id": f"rs_{number}"} for number in range(2)]
        outputs = [response(reasonings[0], calls[0]), response(reasonings[1], calls[1]), response(TEXT)]
        job = with_tools(self.job, [], self.mask, self.skills)
        with mock.patch.object(openai_http, "post_json", side_effect=outputs) as post, \
                mock.patch("chatballs.ai.tool_loop.run_chat", side_effect=dispatch):
            result = run_tool_loop(job, [], self.mask, skills=self.skills)
        self.assertEqual(len(result.rounds), 3)
        self.assertTrue(all(item.error is None for item in result.rounds))
        self.assertEqual(result.rounds[-1].result.text, "Done")
        self.assertEqual(result.tool_calls, ())  # Internal skill loading is not an external action.
        inputs = post.call_args_list[-1].kwargs["payload"]["input"]
        native = [item for item in inputs if item.get("type")]
        self.assertEqual([item["type"] for item in native],
                         ["reasoning", "function_call", "function_call_output"] * 2)
        self.assertEqual(native[0], reasonings[0])
        self.assertEqual(native[3], reasonings[1])
        for index, number in ((2, 0), (5, 1)):
            self.assertEqual(native[index]["call_id"], f"call_{number}")
            self.assertEqual(json.loads(native[index]["output"]), {"instruction": "Ask for the reference"})
        self.assertNotIn("opaque-test-only", json.dumps([request_payload(job) for job in result.requests]))

    def test_external_function_outputs_use_call_id_and_keep_parallel_order(self):
        second = {**CALL, "id": "fc_two", "call_id": "call_two"}
        tools = [SimpleNamespace(spec=TOOL)]
        job = replace(self.job, tools=[TOOL])
        with mock.patch.object(openai_http, "post_json", side_effect=[response(REASONING, CALL, second), response(TEXT)]) as post, \
                mock.patch("chatballs.ai.tool_loop.run_chat", side_effect=dispatch), \
                mock.patch("chatballs.ai.tool_loop.execute_tool_call", side_effect=[('{"ok":1}', "record1"), ('{"ok":2}', "record2")]) as execute:
            result = run_tool_loop(job, tools, self.mask)
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(result.tool_calls, ("record1", "record2"))
        returned = [item for item in post.call_args.kwargs["payload"]["input"] if item.get("type") == "function_call_output"]
        self.assertEqual([item["call_id"] for item in returned], ["call_match", "call_two"])
        self.assertEqual([item["output"] for item in returned], ['{"ok":1}', '{"ok":2}'])

    def test_final_round_forbids_more_tools_without_dropping_history_or_schemas(self):
        outputs = [response(REASONING, {**CALL, "call_id": f"call_{number}", "name": LOAD_SKILL,
                                       "arguments": '{"skill_id": "skill-1"}'}) for number in range(MAX_TOOL_ROUNDS)] + [response(TEXT)]
        job = with_tools(self.job, [], self.mask, self.skills)
        with mock.patch.object(openai_http, "post_json", side_effect=outputs) as post, \
                mock.patch("chatballs.ai.tool_loop.run_chat", side_effect=dispatch):
            result = run_tool_loop(job, [], self.mask, skills=self.skills)
        payload = post.call_args.kwargs["payload"]
        self.assertEqual(payload["tool_choice"], "none")
        self.assertEqual(payload["tools"][0]["name"], LOAD_SKILL)
        self.assertEqual(len(result.rounds), MAX_TOOL_ROUNDS + 1)
        self.assertEqual(sum(item.get("type") == "function_call_output" for item in payload["input"]), MAX_TOOL_ROUNDS)

    def test_diagnostics_remove_all_raw_items_but_keep_public_text_and_usage(self):
        result = openai_responses.parse_response(response(REASONING, CALL, TEXT), model=MODEL)
        payload = chat_payload(result)
        self.assertEqual(payload["text"], "Done")
        self.assertEqual(payload["prompt_tokens"], 12)
        self.assertEqual(payload["tool_calls"][0]["id"], "call_match")
        self.assertNotIn("response_items", payload)
        self.assertNotIn("encrypted_content", json.dumps(payload))
        self.assertEqual(result.response_items[0], REASONING)
