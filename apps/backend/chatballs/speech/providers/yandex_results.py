"""Окончательные сегменты v3, с заменой на normalizedText без дублирования."""

import json

from chatballs.speech.errors import SpeechError


def transcript(content: bytes) -> str:
    decoder = json.JSONDecoder()
    source = content.decode("utf-8")
    records = []
    try:
        while source.strip():
            item, end = decoder.raw_decode(source.lstrip())
            records.extend(item if isinstance(item, list) else [item])
            source = source.lstrip()[end:]
        segments = {}
        for record in records:
            value = record.get("result", record)
            if "error" in value:
                raise SpeechError("provider_error")
            refinement = value.get("finalRefinement")
            if refinement:
                index = int(refinement["finalIndex"])
                result = refinement.get("normalizedText", {})
            elif "final" in value:
                index = int(value.get("audioCursors", {}).get("finalIndex", len(segments)))
                result = value["final"]
            else:
                continue
            alternatives = result.get("alternatives", [])
            if alternatives:
                segments[index] = str(alternatives[0].get("text", "")).strip()
        return " ".join(segments[index] for index in sorted(segments) if segments[index])
    except (ValueError, KeyError, TypeError, AttributeError):
        raise SpeechError("provider_error") from None
