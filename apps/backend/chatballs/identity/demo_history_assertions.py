"""Assertions for the prepared North Wind chats and their weekly report."""

from datetime import timedelta

from django.utils import timezone

from chatballs.conversations.domain_event_models import ConversationEvent
from chatballs.conversations.support_filters import ReportFilters
from chatballs.conversations.support_report import calculate_support_report
from chatballs.identity.demo_seed.north_wind.appointments import MOSCOW
from chatballs.identity.models import OrganizationMembership
from chatballs.tenancy.context import TenantContext


def verify_weekly_reporting(self, conversations):
    today = timezone.now().astimezone(MOSCOW).replace(hour=0, minute=0, second=0, microsecond=0)
    events = ConversationEvent.objects.filter(conversation__in=conversations)
    self.assertFalse(events.filter(event_type="CLOSED").exists())
    member = OrganizationMembership.objects.get(organization=self.organization, user=self.owner)
    context = TenantContext.for_membership(member)
    for age in range(7):
        start = today - timedelta(days=age)
        filters = ReportFilters(start, start + timedelta(days=1), str(MOSCOW))
        report = calculate_support_report(context=context, filters=filters)
        counts = report["totals"]["observedCounts"]
        self.assertGreater(counts["accepted"], 0)
        if age:
            self.assertGreater(counts["completed"], 0)
            self.assertEqual(report["details"], [])
        else:
            self.assertEqual(counts["completed"], 0)

def verify_north_wind_histories(self, conversations):
    outcomes = {
        "pickup": "Заказ № 2048", "loyalty": "Остаток бонусов: 750",
        "fitting": "Запись № 2043", "exchange": "Замену получил",
        "proposal": "Коммерческое предложение № KP-205", "team": "Замена подошла",
        "delivery": "Пока подожду", "formatted": "Заберу после работы",
        "formatted-external": "Новая дата пока не подтверждена", "exchange-refund": "вижу возврат",
    }
    self.assertEqual(conversations.values("contact__name").distinct().order_by().count(), len(outcomes))
    for key, outcome in outcomes.items():
        with self.subTest(scenario=key):
            conversation = conversations.get(external_chat_id__endswith=f":{key}")
            self.assertTrue(conversation.messages.filter(text__contains=outcome).exists())
            self.assertGreaterEqual(conversation.messages.filter(author_type__in=("CONTACT", "OPERATOR", "AI")).count(), 4)
            self.assertTrue(conversation.messages.filter(format_version=1).exists())
            self.assertTrue(conversation.messages.filter(system_event="tool_called", system_params__tool__startswith="MCP").exists())
            self.assertFalse(conversation.messages.filter(text__contains="north-wind.html").exists())
    formatted = conversations.get(external_chat_id__endswith=":formatted")
    self.assertEqual(formatted.messages.filter(format_version=1).count(), 2)
    self.assertEqual(formatted.messages.filter(system_event="tool_called").count(), 4)
    proposal = conversations.get(external_chat_id__endswith=":proposal")
    self.assertTrue(proposal.messages.filter(attachment_name="KP-205.html").exists())
    self.assertTrue(proposal.comments.filter(text__contains="CRM-305").exists())
    for key, count in (("pickup", 4), ("loyalty", 2), ("fitting", 4), ("proposal", 5)):
        dialogue = conversations.get(external_chat_id__endswith=f":{key}")
        cards = dialogue.messages.filter(format_version=1)
        self.assertEqual(cards.count(), count)
        self.assertTrue(all(card.template_snapshot.get("skillId") for card in cards))
    _verify_reusable_card(self)

def _verify_reusable_card(self):
    from chatballs.ai.skill_templates.engine import render_template
    from chatballs.ai.skills_models import Skill

    skill = Skill.objects.get(organization=self.organization, name="Подбор и покупка")
    template = next(item for item in skill.templates if item["name"] == "Карточка товара")
    example = {"title": "Другая модель", "rows": [{"label": "Цена", "value": "35 000 ₽"}]}
    preview = render_template(template, example, language="ru")
    self.assertIn("Другая модель", preview["contentHtml"])
    self.assertIn("Цена: 35 000 ₽", preview["text"])
    self.assertTrue(skill.assignments.filter(agent__channel__organization=self.organization).exists())
