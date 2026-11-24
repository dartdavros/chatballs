"""Reusable Chatballs skills for the cards shown in prepared conversations."""

from uuid import NAMESPACE_URL, uuid5

from chatballs.ai.skill_templates.engine import render_template
from chatballs.ai.skills_models import AgentSkill, Skill
from chatballs.ai.skills_validation import configuration

_HTML = """<div class="card">
{{#if badge}}<span class="badge">{{ badge }}</span>{{/if}}
<h3>{{ title }}</h3>{{#if lead}}<p>{{ lead }}</p>{{/if}}
{{#each rows}}<div class="row"><span class="label">{{ label }}</span><strong>{{ value }}</strong></div>{{/each}}
{{#if detail}}<p class="detail">{{ detail }}</p>{{/if}}
</div>"""
_TEXT = """{{#if badge}}{{ badge }}
{{/if}}{{ title }}{{#if lead}}
{{ lead }}{{/if}}
{{#each rows}}{{ label }}: {{ value }}
{{/each}}{{#if detail}}{{ detail }}{{/if}}"""

_CSS = """
html,body{background:#fff;font-size:14px;line-height:1.55;font-family:Arial,sans-serif}
.card{padding:16px;border:1px solid #dbe5e7;border-radius:12px;color:#23303b}
.badge{display:inline-block;padding:4px 8px;border-radius:6px;background:#eaf4ef;color:#33765e;font-size:12px;font-weight:600;margin-bottom:10px}
h3{font-size:18px;line-height:1.3;margin:0 0 8px}p{margin:0 0 8px}
.row{display:flex;justify-content:space-between;gap:12px;margin:7px 0}
.row strong{text-align:right;overflow-wrap:anywhere}.label,.detail{color:#697586}
.detail{font-size:12px;margin:9px 0 0}
"""


def load_history_skills(refs, definitions, dialogues):
    samples = {}
    for rows in dialogues.values():
        for kind, item in rows:
            if kind == "snapshot":
                examples = samples.setdefault(item["template"], [])
                if len(examples) < 2:
                    examples.append(card_data(item))

    templates = {}
    for definition in definitions:
        skill = create_history_skill(refs, {
            "name": definition["name"], "description": definition["description"],
            "instruction": definition["instruction"],
            "templates": [_template(key, label, samples[key]) for key, label in definition["templates"].items()],
        })
        for agent_key in definition["agents"]:
            AgentSkill.objects.create(organization=refs.organization, agent=refs.agents[agent_key], skill=skill)
        templates.update(zip(definition["templates"], ((skill, item) for item in skill.templates), strict=True))
    return templates


def create_history_skill(refs, values):
    dataset = refs.recorder.dataset
    values = configuration(values)
    template_ids = dataset.shop_state.setdefault("historyTemplateIds", [])
    for template in values["templates"]:
        template["id"] = history_template_id(dataset, template["id"])
        template_ids.append(template["id"])
    return Skill.objects.create(organization_id=dataset.organization_id, **values)


def history_template_id(dataset, source_id):
    return str(uuid5(dataset.generation, f"history-template/{source_id}"))


def _template(key, label, examples):
    text = {"type": "string"}
    required = {**text, "required": True}
    rows = {"type": "list", "required": True,
            "items": {"type": "object", "properties": {"label": required, "value": required}}}
    return {
        "id": str(uuid5(NAMESPACE_URL, f"chatballs.demo.north-wind/{key}")),
        "name": label["name"], "purpose": label["purpose"], "css": _CSS, "html": _HTML, "text": _TEXT,
        "schema": {"type": "object", "properties": {
            "title": required, "badge": text, "lead": text, "rows": rows, "detail": text,
        }},
        "examples": examples,
    }


def card_data(item):
    return {**{key: item[key] for key in ("title", "badge", "lead", "detail") if key in item},
            "rows": [{"label": label, "value": value} for label, value in item["rows"]]}


def snapshot_fields(skill, template, values, language):
    result = render_template(template, values, language=language)
    return {
        "text": result["text"], "content_html": result["contentHtml"], "presentation": result["presentation"],
        "format_version": 1, "delivery_representation": "html",
        "template_snapshot": {"id": template["id"], "name": template["name"],
                              "skillId": str(skill.public_id), "skillRevision": skill.revision},
    }
