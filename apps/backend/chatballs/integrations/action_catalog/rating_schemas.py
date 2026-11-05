"""Customer scales and protected score history use distinct typed outputs."""

from dataclasses import replace

from chatballs.integrations.action_catalog.schema import BOOLEAN, TEXT, obj, required
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

INTEGER = TypeSpec("integer")
DATE = TypeSpec("datetime", nullable=True)
SCORE = TypeSpec("enum", options=tuple(EnumOption(value, f"native.rating_score.{value}") for value in range(1, 6)))
SCALE = TypeSpec("array", max_items=5, items=obj(value=required(INTEGER), label=required(replace(TEXT, max_length=120))))
RESULT = obj(value=SCORE, comment=TEXT, receivedAt=TypeSpec("datetime"))
PROTECTED = replace(RESULT, properties=RESULT.properties + obj(id=INTEGER, requestId=TEXT, conversationId=INTEGER,
    completionId=INTEGER, responderIds=TypeSpec("array", items=INTEGER), scale=SCALE,
    responders=TypeSpec("array", items=obj(id=INTEGER, name=TEXT, avatarUrl=TypeSpec("string", nullable=True)))).properties)
SETTINGS_FIELDS = dict(enabled=BOOLEAN, scale=SCALE, text=replace(TEXT, max_length=4000), delaySeconds=INTEGER)
SETTINGS = obj(**SETTINGS_FIELDS, updatedAt=DATE, updatedBy=TEXT,
    defaults=obj(scale=SCALE, text=TEXT, delaySeconds=INTEGER))
QUESTION = obj(text=TEXT, scale=SCALE, expiresAt=TypeSpec("datetime"), commentMaxLength=INTEGER,
    result=replace(RESULT, nullable=True), presentation=obj(name=TEXT, accent=TEXT, siteUrl=TEXT,
        conversationDate=TypeSpec("datetime"), language=TEXT))
GROUP = obj(scaleId=TEXT, scale=SCALE, count=INTEGER,
    values=TypeSpec("array", items=obj(value=SCORE, count=INTEGER)))
RESULTS = obj(count=INTEGER, scaleGroups=TypeSpec("array", items=GROUP), results=TypeSpec("array", items=PROTECTED))
CARD = obj(results=TypeSpec("array", items=PROTECTED), request=replace(obj(sentAt=DATE), nullable=True), enabled=BOOLEAN)
