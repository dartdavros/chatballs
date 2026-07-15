"""Импорт AI-контента из content/*.md в Знания и агентов (ADR-HUB-0023).

Файлы контента размечены секциями `=== code ===` (SPEC-HUB-0012):
- prompt-секции (system-*, qualify-*, sales-*, handoff-*) заполняют пустые поля
  persona/instructions агента соответствующего канала — уже заполненные поля
  не перезаписываются (владелец правит их через UI);
- остальные секции становятся Знаниями (upsert по заголовку = коду секции)
  и добавляются в выбор знаний агентов: глобальные — всем каналам,
  продуктовые — каналам своего продукта.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction

from hub_platform.ai import indexing
from hub_platform.ai.models import Knowledge
from hub_platform.tenancy.context import TenantContext

_SECTION_RE = re.compile(r"^===\s*(?P<code>[a-z0-9-]+)\s*===\s*$", re.MULTILINE)

_PROMPT_PREFIXES = ("system", "qualify", "sales", "handoff")
# Суффикс prompt-секции -> код продукта канала (None — непродуктовый канал edevs).
_PRODUCT_BY_SUFFIX = {"edevs": None, "foxray": "foxray", "firepage": "firepage"}
# Префикс knowledge-секции -> код продукта (нет префикса в карте — глобальное знание).
_PRODUCT_BY_PREFIX = {"foxray": "foxray", "firepage": "firepage"}

CONTENT_SOURCES = (
    "content/ai-content-company-filled.md",
    "content/ai-content-firepage-filled.md",
    "content/ai-content-foxray-filled.md",
)


@dataclass(frozen=True)
class ImportResult:
    knowledge_created: int = 0
    knowledge_updated: int = 0
    fragments_created: int = 0
    agents_updated: int = 0
    skipped_sections: int = 0

    def add(self, other: "ImportResult") -> "ImportResult":
        return ImportResult(
            knowledge_created=self.knowledge_created + other.knowledge_created,
            knowledge_updated=self.knowledge_updated + other.knowledge_updated,
            fragments_created=self.fragments_created + other.fragments_created,
            agents_updated=self.agents_updated + other.agents_updated,
            skipped_sections=self.skipped_sections + other.skipped_sections,
        )


def parse_filled_content(text: str) -> dict[str, str]:
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        code = match.group("code")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            sections[code] = content
    return sections


def _import_knowledge(*, organization, code: str, content: str) -> tuple[Knowledge, ImportResult]:
    knowledge = Knowledge.objects.filter(organization=organization, title=code).first()
    if knowledge is None:
        knowledge = Knowledge.objects.create(organization=organization, title=code, content=content)
        fragments = indexing.reindex_knowledge(knowledge)
        return knowledge, ImportResult(knowledge_created=1, fragments_created=len(fragments))
    if knowledge.content == content:
        return knowledge, ImportResult()
    knowledge.content = content
    knowledge.save(update_fields=["content", "updated_at"])
    fragments = indexing.reindex_knowledge(knowledge)
    return knowledge, ImportResult(knowledge_updated=1, fragments_created=len(fragments))


def _agents_for_product(*, organization, product_code: str | None):
    from hub_platform.ai.models import AIAgent

    queryset = AIAgent.objects.select_related("channel").filter(channel__organization=organization)
    if product_code is None:
        return queryset.filter(channel__product__isnull=True)
    return queryset.filter(channel__product__code=product_code)


def _apply_prompts(*, organization, prompts: dict[tuple[str | None, str], str]) -> int:
    """prompts: (product_code|None, kind) -> content. Заполняет только пустые поля."""
    updated = 0
    product_codes = {key[0] for key in prompts}
    for product_code in product_codes:
        persona = prompts.get((product_code, "system"), "")
        instruction_parts = [
            prompts[(product_code, kind)]
            for kind in ("qualify", "sales", "handoff")
            if (product_code, kind) in prompts
        ]
        instructions = "\n\n".join(instruction_parts)
        for agent in _agents_for_product(organization=organization, product_code=product_code):
            fields = []
            if persona and not agent.persona.strip():
                agent.persona = persona
                fields.append("persona")
            if instructions and not agent.instructions.strip():
                agent.instructions = instructions
                fields.append("instructions")
            if fields:
                agent.save(update_fields=[*fields, "updated_at"])
                updated += 1
    return updated


def _assign_knowledge(*, organization, global_items: list[Knowledge], by_product: dict[str, list[Knowledge]]) -> None:
    from hub_platform.ai.models import AIAgent

    for agent in AIAgent.objects.select_related("channel__product").filter(channel__organization=organization):
        items = list(global_items)
        if agent.channel.product_id:
            items += by_product.get(agent.channel.product.code, [])
        if items:
            agent.knowledge_items.add(*items)


@transaction.atomic
def import_ai_content(*, base_dir: Path, context: TenantContext) -> ImportResult:
    organization = context.organization
    result = ImportResult()
    prompts: dict[tuple[str | None, str], str] = {}
    global_items: list[Knowledge] = []
    by_product: dict[str, list[Knowledge]] = {}

    for relative_path in CONTENT_SOURCES:
        path = base_dir / relative_path
        if not path.exists():
            continue
        for code, content in parse_filled_content(path.read_text(encoding="utf-8")).items():
            parts = code.split("-")
            if len(parts) < 2:
                result = result.add(ImportResult(skipped_sections=1))
                continue
            if parts[0] in _PROMPT_PREFIXES:
                suffix = parts[-1]
                if suffix not in _PRODUCT_BY_SUFFIX:
                    result = result.add(ImportResult(skipped_sections=1))
                    continue
                prompts[(_PRODUCT_BY_SUFFIX[suffix], parts[0])] = content
                continue
            knowledge, section_result = _import_knowledge(organization=organization, code=code, content=content)
            result = result.add(section_result)
            product_code = _PRODUCT_BY_PREFIX.get(parts[0])
            if product_code is None:
                global_items.append(knowledge)
            else:
                by_product.setdefault(product_code, []).append(knowledge)

    agents_updated = _apply_prompts(organization=organization, prompts=prompts)
    _assign_knowledge(organization=organization, global_items=global_items, by_product=by_product)
    return result.add(ImportResult(agents_updated=agents_updated))
