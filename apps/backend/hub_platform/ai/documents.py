from django.db import transaction

from hub_platform.ai.models import DocumentStatus


def _next_version(version_model, document) -> int:
    last = version_model.objects.filter(document=document).order_by("-version").first()
    return last.version + 1 if last is not None else 1


@transaction.atomic
def create_document(*, document_model, version_model, content, author, **fields):
    document = document_model.objects.create(**fields)
    version_model.objects.create(
        document=document, version=1, content=content, status=DocumentStatus.DRAFT, created_by=author
    )
    return document


@transaction.atomic
def add_version(*, version_model, document, content, author):
    return version_model.objects.create(
        document=document,
        version=_next_version(version_model, document),
        content=content,
        status=DocumentStatus.DRAFT,
        created_by=author,
    )


@transaction.atomic
def publish_version(*, version):
    # Один опубликованный документ за раз: прежние публикации архивируем.
    type(version).objects.filter(document=version.document, status=DocumentStatus.PUBLISHED).exclude(
        pk=version.pk
    ).update(status=DocumentStatus.ARCHIVED)
    version.status = DocumentStatus.PUBLISHED
    version.save(update_fields=["status"])
    return version


@transaction.atomic
def rollback_document(*, version_model, document, source_version, author):
    # Откат создаёт новый черновик из содержимого старой версии (ADR-HUB-0005/0007).
    return version_model.objects.create(
        document=document,
        version=_next_version(version_model, document),
        content=source_version.content,
        status=DocumentStatus.DRAFT,
        created_by=author,
    )
