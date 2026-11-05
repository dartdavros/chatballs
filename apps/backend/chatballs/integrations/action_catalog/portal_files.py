"""Portal attachments retain storage quotas and common execution file ownership."""

from functools import partial

from django.core.files.uploadedfile import SimpleUploadedFile

from chatballs.integrations.action_catalog.file_reads import FILE_RESULT, stream_result
from chatballs.integrations.action_catalog.portal_content_schemas import ARTICLE_ID, FILE
from chatballs.integrations.action_catalog.portal_operations import article, invoke
from chatballs.integrations.action_catalog.portal_schemas import ID, field, named
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.adapters.contracts import Effect
from chatballs.support_portals.content_services import add_article_file, delete_article_file
from chatballs.support_portals.models import PortalArticleFile
from chatballs.support_portals.serializers import article_file_payload


def listing(context, values):
    return {"items": [article_file_payload(row) for row in article(context, values).files.all()]}


def upload(context, values):
    row = article(context, values)
    name, content_type, content = context.open_file(values["file"]["fileId"])
    saved = add_article_file(context=context.tenant, article=row,
        upload=SimpleUploadedFile(name, content, content_type), author=context.tenant.actor_user)
    return {"file": article_file_payload(saved)}


def delete(context, values):
    row = article(context, values).files.get(pk=values["file_id"])
    delete_article_file(context=context.tenant, article_file=row)
    return {}


def download(context, values):
    # The public file route uses the unguessable UUID, including draft files.
    # Native access additionally requires the canonical execution organization.
    row = PortalArticleFile.objects.get(public_id=values["public_id"],
        organization_id=context.tenant.organization_id, article__organization_id=context.tenant.organization_id)
    return stream_result(context, row.file.open("rb"), row.original_name, row.content_type)


TARGET = dict(portal_id=ID, article_id=ARTICLE_ID)
for key, method, route, view, inputs, outputs, service, effect, execution in (
    ("portals.article.files.get", "GET", "", "ArticleFileListView", obj(**TARGET),
        obj(items=field("files", "array", items=FILE)), listing, Effect.READ, "local"),
    ("portals.article.files.post", "POST", "", "ArticleFileListView",
        obj(**TARGET, file=field("file", "file", required=True)), obj(file=named("file", FILE)), upload, Effect.CREATE, "io"),
    ("portals.article.file.delete", "DELETE", "<int:file_id>/", "ArticleFileDetailView",
        obj(**TARGET, file_id=field("file", "integer", required=True)), obj(), delete, Effect.DELETE, "io"),
):
    capability = "support.view" if method == "GET" else "support.operate"
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(invoke, service=service, capability=capability), capability=capability, scope="organization",
        route=f"support/portals/<int:portal_id>/articles/<int:article_id>/files/{route}",
        view=f"chatballs.support_portals.content_views.{view}", method=method, effect=effect, execution=execution)

action(key="portals.file.get", title="native.portals.file.get", input=obj(public_id=field("publicId", required=True)),
    output=FILE_RESULT, handler=partial(invoke, service=download, capability=""), capability="", scope="organization",
    route="api/v1/help/files/<uuid:public_id>/", view="chatballs.support_portals.file_views.PortalArticleFileView",
    method="GET", effect=Effect.READ, execution="io")
