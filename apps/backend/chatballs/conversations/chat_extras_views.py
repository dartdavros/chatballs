"""Дизайн-базлайн v2: приоритет, метки, заметка, архив, шаблоны, счётчики.

Решения владельца (2026-09-04): метки и приоритет входят в модель; «удалить
диалог» = архив, архив видят только администраторы; шаблоны ответов общие на
организацию (редактируют администраторы, используют все).
"""

from __future__ import annotations

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.conversations.models import (
    ControlMode,
    Conversation,
    ConversationLabel,
    ConversationPriority,
    LifecycleState,
    ReplyTemplate,
)
from chatballs.conversations.selectors import apply_conversation_visibility
from chatballs.conversations.serializers import conversation_payload
from chatballs.conversations.view_base import ConversationViewBase
from chatballs.i18n import t
from chatballs.identity.avatars import user_avatar_url
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.models import HumanUser, OrganizationMembership
from chatballs.identity.policy import can_administer_access


def _label_payload(label: ConversationLabel) -> dict[str, object]:
    return {"id": label.id, "name": label.name, "color": label.color}


def _template_payload(template: ReplyTemplate) -> dict[str, object]:
    return {
        "id": template.id,
        "title": template.title,
        "text": template.text,
        "updatedAt": template.updated_at.isoformat(),
    }


class ConversationPriorityView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        priority = str(request.data.get("priority", "")).strip().upper()
        if priority not in ConversationPriority.values:
            return Response({"detail": t("conversations.unknown_priority")}, status=400)
        conversation.priority = priority
        conversation.save(update_fields=["priority"])
        self._audit(request, "priority_changed", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )


class ConversationContactView(ConversationViewBase):
    """Карточка контакта из диалога (дизайн-базлайн v2, карандаш у имени):
    имя, описание, телефон, компания, город."""

    required_capability = "conversations.operate"
    LIMITS = {"name": 255, "description": 2000, "phone": 32, "company": 160, "city": 120}

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        contact = conversation.contact
        if contact is None:
            return Response({"detail": t("conversations.no_contact")}, status=400)
        changed: list[str] = []
        for field, limit in self.LIMITS.items():
            if field not in request.data:
                continue
            value = str(request.data.get(field) or "").strip()
            if len(value) > limit:
                return Response({"detail": f"Поле {field}: не длиннее {limit} символов"}, status=400)
            if field == "name" and not value:
                return Response({"detail": t("conversations.contact_name_empty")}, status=400)
            setattr(contact, field, value)
            changed.append(field)
        if changed:
            contact.save(update_fields=changed)
            self._audit(request, "contact_updated", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )


class ConversationNoteView(ConversationViewBase):
    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        note = str(request.data.get("note", ""))
        if len(note) > 4000:
            return Response({"detail": t("conversations.note_too_long")}, status=400)
        conversation.note = note
        conversation.note_author = request.user if note else None
        conversation.note_updated_at = timezone.now() if note else None
        conversation.save(update_fields=["note", "note_author", "note_updated_at"])
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )


class ConversationLabelsView(ConversationViewBase):
    """Полная замена набора меток диалога (чипы в карточке)."""

    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        label_ids = request.data.get("labelIds")
        if not isinstance(label_ids, list) or not all(
            isinstance(item, int) for item in label_ids
        ):
            return Response({"detail": "labelIds must be a list of ids"}, status=400)
        labels = list(
            ConversationLabel.objects.filter(
                organization_id=request.tenant_context.organization_id,
                id__in=set(label_ids),
            )
        )
        if len(labels) != len(set(label_ids)):
            return Response({"detail": t("conversations.unknown_label")}, status=400)
        conversation.labels.set(labels)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )


class ConversationArchiveView(ConversationViewBase):
    """«Удалить диалог» = архив: скрыт из списков, восстановить может только
    администратор."""

    required_capability = "conversations.operate"

    def post(self, request: Request, conversation_id: int) -> Response:
        try:
            conversation = self._conversation(
                request, conversation_id, self.required_capability
            )
        except Conversation.DoesNotExist:
            return Response({"detail": t("conversations.not_found")}, status=404)
        archived = request.data.get("archived")
        if not isinstance(archived, bool):
            return Response({"detail": "archived must be a boolean"}, status=400)
        if not archived and not can_administer_access(request.tenant_context.membership):
            return Response(
                {"detail": t("conversations.restore_admin_only")}, status=403
            )
        conversation.archived_at = timezone.now() if archived else None
        conversation.save(update_fields=["archived_at"])
        self._audit(request, "archived" if archived else "unarchived", conversation)
        return Response(
            {
                "conversation": conversation_payload(
                    conversation, detailed=True, viewer_id=request.user.id
                )
            }
        )


class ConversationCountersView(ConversationViewBase):
    """Счётчики для дерева фильтров (сайдбар сотрудника / охват админа)."""

    def get(self, request: Request) -> Response:
        # Чистый queryset без инбокс-аннотаций: values().annotate() иначе
        # группировал бы по _last_message_at.
        base = (
            apply_conversation_visibility(
                Conversation.objects.filter(
                    organization_id=request.tenant_context.organization_id
                ),
                request.tenant_context,
            )
            .filter(archived_at__isnull=True)
            .exclude(lifecycle=LifecycleState.SPAM)
            .order_by()
        )
        open_qs = base.filter(lifecycle=LifecycleState.OPEN)
        groups = [
            {"id": row["group_id"], "name": row["group__name"], "color": row["group__color"], "count": row["count"]}
            for row in open_qs.filter(group__isnull=False)
            .values("group_id", "group__name", "group__color")
            .annotate(count=Count("id"))
            .order_by("group__name")
        ]
        ungrouped = open_qs.filter(group__isnull=True).count()
        agents = [
            {
                "id": row["channel_id"],
                "code": row["channel__code"],
                "name": row["channel__name"],
                "count": row["count"],
            }
            for row in open_qs.values("channel_id", "channel__code", "channel__name")
            .annotate(count=Count("id"))
            .order_by("channel__name")
        ]
        # Секция «Ответственный» поповера охвата (A1): кто сколько ведёт.
        assignees = [
            {
                "id": row["assigned_operator_id"],
                "name": row["assigned_operator__full_name"] or row["assigned_operator__email"],
                "count": row["count"],
            }
            for row in open_qs.filter(assigned_operator__isnull=False)
            .values("assigned_operator_id", "assigned_operator__full_name", "assigned_operator__email")
            .annotate(count=Count("id"))
            .order_by("-count", "assigned_operator__full_name")
        ]
        avatars = {
            user.id: user
            for user in HumanUser.objects.filter(id__in=[a["id"] for a in assignees]).exclude(avatar="")
        }
        for assignee in assignees:
            assignee["avatarUrl"] = user_avatar_url(avatars.get(assignee["id"]), request.tenant_context.organization.public_id)
        return Response(
            {
                "all": open_qs.count(),
                "waiting": open_qs.filter(control_mode=ControlMode.PAUSED).count(),
                "mine": base.filter(assigned_operator_id=request.user.id).count(),
                "ungrouped": ungrouped,
                "groups": groups,
                "agents": agents,
                "assignees": assignees,
            }
        )


# Справочник выбора: ростер организации может быть большим, поэтому список
# коллег ограничен и ищется на сервере — в выборе стоит строка поиска (кадр G).
DIRECTORY_LIMIT = 50


class ConversationDirectoryView(APIView):
    """Справочник блока «Диалог» для оператора (дизайн-базлайн v2, кадр G):
    все группы организации — для переноса, активные коллеги — для назначения.
    Доступен любому, кто видит чат: менеджерские списки сотрудников и групп
    сотруднику закрыты, а переносить и назначать он может."""

    permission_classes = [HasCapability]
    required_capabilities = {"GET": "conversations.view"}

    def get(self, request: Request) -> Response:
        organization_id = request.tenant_context.organization_id
        groups = EmployeeGroup.objects.filter(organization_id=organization_id).order_by("name")
        members = (
            OrganizationMembership.objects.select_related("user")
            .filter(organization_id=organization_id, blocked_at__isnull=True, user__is_active=True)
            .order_by("user__full_name", "user__email")
        )
        query = request.query_params.get("q", "").strip()
        if query:
            members = members.filter(
                Q(user__full_name__icontains=query) | Q(user__email__icontains=query)
            )
        # Ответственного можно назначить и вне выдачи — по поиску, поэтому
        # оставшихся не прячем молча, а сообщаем признаком hasMore.
        rows = list(members[: DIRECTORY_LIMIT + 1])
        return Response(
            {
                "groups": [{"id": group.id, "name": group.name, "color": group.color} for group in groups],
                "employees": [
                    {
                        "id": member.user_id,
                        "name": member.user.full_name or member.user.email,
                        "avatarUrl": user_avatar_url(member.user, request.tenant_context.organization.public_id),
                    }
                    for member in rows[:DIRECTORY_LIMIT]
                ],
                "hasMoreEmployees": len(rows) > DIRECTORY_LIMIT,
            }
        )


class LabelListView(APIView):
    """Словарь меток организации. Создание — лёгкое действие оператора
    («+ Добавить» в карточке), правка/удаление — администратора."""

    permission_classes = [HasCapability]
    required_capabilities = {
        "GET": "conversations.view",
        "POST": "conversations.operate",
    }

    def get(self, request: Request) -> Response:
        labels = ConversationLabel.objects.filter(
            organization_id=request.tenant_context.organization_id
        )
        return Response({"items": [_label_payload(label) for label in labels]})

    def post(self, request: Request) -> Response:
        name = str(request.data.get("name", "")).strip()
        color = str(request.data.get("color", "")).strip()
        if not name or len(name) > 60:
            return Response({"detail": t("conversations.label_name_length")}, status=400)
        if len(color) > 20:
            return Response({"detail": t("conversations.invalid_colour")}, status=400)
        existing = ConversationLabel.objects.filter(
            organization_id=request.tenant_context.organization_id, name__iexact=name
        ).first()
        if existing is not None:
            return Response({"label": _label_payload(existing)})
        label = ConversationLabel.objects.create(
            organization_id=request.tenant_context.organization_id,
            name=name,
            color=color,
        )
        return Response({"label": _label_payload(label)}, status=201)


class LabelDetailView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"PATCH": "settings.manage", "DELETE": "settings.manage"}

    def _label(self, request: Request, label_id: int) -> ConversationLabel:
        return ConversationLabel.objects.get(
            organization_id=request.tenant_context.organization_id, id=label_id
        )

    def patch(self, request: Request, label_id: int) -> Response:
        try:
            label = self._label(request, label_id)
        except ConversationLabel.DoesNotExist:
            return Response({"detail": t("conversations.label_not_found")}, status=404)
        if "name" in request.data:
            name = str(request.data.get("name", "")).strip()
            if not name or len(name) > 60:
                return Response({"detail": t("conversations.label_name_length")}, status=400)
            label.name = name
        if "color" in request.data:
            color = str(request.data.get("color", "")).strip()
            if len(color) > 20:
                return Response({"detail": t("conversations.invalid_colour")}, status=400)
            label.color = color
        label.save()
        return Response({"label": _label_payload(label)})

    def delete(self, request: Request, label_id: int) -> Response:
        try:
            label = self._label(request, label_id)
        except ConversationLabel.DoesNotExist:
            return Response({"detail": t("conversations.label_not_found")}, status=404)
        label.delete()
        return Response(status=204)


class ReplyTemplateListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {
        "GET": "conversations.view",
        "POST": "settings.manage",
    }

    def get(self, request: Request) -> Response:
        templates = ReplyTemplate.objects.filter(
            organization_id=request.tenant_context.organization_id
        )
        return Response({"items": [_template_payload(item) for item in templates]})

    def post(self, request: Request) -> Response:
        title = str(request.data.get("title", "")).strip()
        text = str(request.data.get("text", "")).strip()
        if not title or len(title) > 120:
            return Response({"detail": t("conversations.template_name_length")}, status=400)
        if not text:
            return Response({"detail": t("conversations.template_text_required")}, status=400)
        if ReplyTemplate.objects.filter(
            organization_id=request.tenant_context.organization_id, title__iexact=title
        ).exists():
            return Response({"detail": t("conversations.template_name_taken")}, status=409)
        template = ReplyTemplate.objects.create(
            organization_id=request.tenant_context.organization_id,
            title=title,
            text=text,
        )
        return Response({"template": _template_payload(template)}, status=201)


class ReplyTemplateDetailView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"PATCH": "settings.manage", "DELETE": "settings.manage"}

    def _template(self, request: Request, template_id: int) -> ReplyTemplate:
        return ReplyTemplate.objects.get(
            organization_id=request.tenant_context.organization_id, id=template_id
        )

    def patch(self, request: Request, template_id: int) -> Response:
        try:
            template = self._template(request, template_id)
        except ReplyTemplate.DoesNotExist:
            return Response({"detail": t("conversations.template_not_found")}, status=404)
        if "title" in request.data:
            title = str(request.data.get("title", "")).strip()
            if not title or len(title) > 120:
                return Response({"detail": t("conversations.template_name_length")}, status=400)
            template.title = title
        if "text" in request.data:
            text = str(request.data.get("text", "")).strip()
            if not text:
                return Response({"detail": t("conversations.template_text_required")}, status=400)
            template.text = text
        template.save()
        return Response({"template": _template_payload(template)})

    def delete(self, request: Request, template_id: int) -> Response:
        try:
            template = self._template(request, template_id)
        except ReplyTemplate.DoesNotExist:
            return Response({"detail": t("conversations.template_not_found")}, status=404)
        template.delete()
        return Response(status=204)
