"""Article, revision, import and file contracts."""

from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.portal_schemas import CATEGORY, ID, STATUS, field, named
from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.schema import TypeSpec

ARTICLE_ID = field("article", "integer", required=True)
REVISION_FIELDS = dict(title=field("title"), summary=field("summary"), content=field("content"))
REVISION = obj(**REVISION_FIELDS, id=field("revision", "integer"), revision=field("revisionNumber", "integer"),
    createdAt=field("createdAt", "datetime"), publishedAt=field("publishedAt", "datetime", nullable=True),
    authorName=field("authorName"))
FILE = obj(id=field("file", "integer"), name=field("name"), contentType=field("contentType"),
    size=field("size", "integer"), path=field("path"), url=field("publicUrl"), createdAt=field("createdAt", "datetime"))
EDIT = dict(categoryId=field("category", "integer"), slug=field("slug"), locale=field("locale"),
    sortOrder=field("sortOrder", "integer"), relatedArticleIds=field("relatedArticles", "array", items=TypeSpec("integer")))
ARTICLE = obj(id=field("article", "integer"), slug=EDIT["slug"], locale=EDIT["locale"],
    sortOrder=EDIT["sortOrder"], relatedArticleIds=EDIT["relatedArticleIds"], status=STATUS,
    category=named("category", CATEGORY), publishedRevision=named("publishedRevision", REVISION, nullable=True),
    latestRevision=named("latestRevision", REVISION, nullable=True),
    createdAt=field("createdAt", "datetime"), updatedAt=field("updatedAt", "datetime"),
    feedback=named("feedback", obj(helpful=field("helpful", "integer"), unhelpful=field("unhelpful", "integer"))),
    fileCount=field("fileCount", "integer"), files=field("files", "array", items=FILE),
    revisions=field("revisions", "array", items=REVISION))
OUTPUT = obj(article=named("article", ARTICLE))
PAGE = page_of(ARTICLE)
FILTERS = obj(portal_id=ID, **PAGE_INPUTS, q=field("search"), category=field("category", "integer"),
    locale=field("locale", "array", items=TypeSpec("string")), status=field("status", "array", items=STATUS))
DOCUMENT = obj(slug=field("slug", required=True), title=field("title", required=True),
    content=field("content"), summary=field("summary", nullable=True), locale=field("locale", nullable=True),
    categoryPath=field("categoryPath", "array", required=True, items=TypeSpec("string")))
IMPORT = obj(portal_id=ID, articles=field("articles", "array", required=True, min_items=1, items=DOCUMENT))
IMPORT_RESULT = obj(created=field("created", "integer"), updated=field("updated", "integer"),
    unchanged=field("unchanged", "integer"), failed=field("failed", "array", items=obj(slug=field("slug"), detail=field("error"))))
