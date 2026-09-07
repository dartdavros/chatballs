from django.core.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.support_portals.api import validation_response
from chatballs.support_portals.content_services import (
    add_article_file,
    add_revision,
    archive_article,
    create_article,
    create_category,
    delete_article_file,
    delete_category,
    publish_revision,
    update_article,
    update_category,
)
from chatballs.support_portals.models import PortalArticle
from chatballs.support_portals.portal_views import PortalBaseView
from chatballs.support_portals.selectors import category_article_counts
from chatballs.support_portals.serializers import (
    article_file_payload,
    article_payload,
    category_payload,
    revision_payload,
)


def _article(portal, article_id: int) -> PortalArticle | None:
    return (
        portal.articles.select_related("portal", "category", "published_revision")
        .prefetch_related("revisions", "revisions__created_by", "files", "feedback")
        .filter(id=article_id)
        .first()
    )


class CategoryListView(PortalBaseView):
    def get(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        counts = category_article_counts(portal)
        return Response(
            {
                "items": [
                    category_payload(item, article_count=counts.get(item.id, 0))
                    for item in portal.categories.all()
                ]
            }
        )

    def post(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        try:
            category = create_category(
                context=request.tenant_context,
                portal=portal,
                data=request.data,
            )
        except (ValidationError, TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                return validation_response(error)
            return Response({"detail": "Некорректная категория"}, status=400)
        return Response({"category": category_payload(category)}, status=201)


class CategoryDetailView(PortalBaseView):
    def _category(self, request: Request, portal_id: int, category_id: int):
        portal = self.portal(request, portal_id)
        if portal is None:
            return None, None
        return portal, portal.categories.filter(id=category_id).first()

    def patch(
        self, request: Request, portal_id: int, category_id: int
    ) -> Response:
        portal, category = self._category(request, portal_id, category_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        if category is None:
            return Response({"detail": "Раздел не найден"}, status=404)
        try:
            category = update_category(
                portal=portal, category=category, data=request.data
            )
        except (ValidationError, TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                return validation_response(error)
            return Response({"detail": "Некорректный раздел"}, status=400)
        return Response({"category": category_payload(category)})

    def delete(
        self, request: Request, portal_id: int, category_id: int
    ) -> Response:
        portal, category = self._category(request, portal_id, category_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        if category is None:
            return Response({"detail": "Раздел не найден"}, status=404)
        try:
            delete_category(portal=portal, category=category)
        except ValidationError as error:
            return validation_response(error)
        return Response(status=204)


class ArticleListView(PortalBaseView):
    def get(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        articles = portal.articles.select_related(
            "category", "published_revision"
        ).prefetch_related("revisions", "files", "feedback").all()
        return Response({"items": [article_payload(item) for item in articles]})

    def post(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        try:
            article = create_article(
                context=request.tenant_context,
                portal=portal,
                data=request.data,
            )
        except (ValidationError, TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                return validation_response(error)
            return Response({"detail": "Некорректная статья"}, status=400)
        article = _article(portal, article.id)
        return Response(
            {"article": article_payload(article, revisions=True, files=True)},
            status=201,
        )


class ArticleDetailView(PortalBaseView):
    def get(self, request: Request, portal_id: int, article_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        article = _article(portal, article_id)
        if article is None:
            return Response({"detail": "Статья не найдена"}, status=404)
        return Response({"article": article_payload(article, revisions=True, files=True)})

    def patch(self, request: Request, portal_id: int, article_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        article = _article(portal, article_id)
        if article is None:
            return Response({"detail": "Статья не найдена"}, status=404)
        try:
            article = update_article(article=article, data=request.data)
        except (ValidationError, TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                return validation_response(error)
            return Response({"detail": "Некорректные данные статьи"}, status=400)
        article = _article(portal, article.id)
        return Response({"article": article_payload(article, revisions=True, files=True)})


class ArticleRevisionListView(PortalBaseView):
    def post(self, request: Request, portal_id: int, article_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        article = _article(portal, article_id)
        if article is None:
            return Response({"detail": "Статья не найдена"}, status=404)
        try:
            revision = add_revision(
                context=request.tenant_context,
                article=article,
                data=request.data,
                author=request.user,
            )
        except ValidationError as error:
            return validation_response(error)
        return Response({"revision": revision_payload(revision)}, status=201)


class ArticlePublishView(PortalBaseView):
    def post(self, request: Request, portal_id: int, article_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        article = _article(portal, article_id)
        if article is None:
            return Response({"detail": "Статья не найдена"}, status=404)
        try:
            article = publish_revision(
                article=article,
                revision_id=int(request.data.get("revisionId", 0)),
            )
        except (ValidationError, TypeError, ValueError) as error:
            if isinstance(error, ValidationError):
                return validation_response(error)
            return Response({"detail": "Некорректная версия"}, status=400)
        article = _article(portal, article.id)
        return Response({"article": article_payload(article, revisions=True, files=True)})


class ArticleArchiveView(PortalBaseView):
    def post(self, request: Request, portal_id: int, article_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        article = _article(portal, article_id)
        if article is None:
            return Response({"detail": "Статья не найдена"}, status=404)
        article = archive_article(article)
        return Response({"article": article_payload(article, revisions=True, files=True)})


class ArticleFileListView(PortalBaseView):
    """Файлы статьи портала: список и загрузка (кадры PT7/PT8)."""

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request: Request, portal_id: int, article_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        article = _article(portal, article_id)
        if article is None:
            return Response({"detail": "Статья не найдена"}, status=404)
        return Response(
            {"items": [article_file_payload(item) for item in article.files.all()]}
        )

    def post(self, request: Request, portal_id: int, article_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        article = _article(portal, article_id)
        if article is None:
            return Response({"detail": "Статья не найдена"}, status=404)
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"detail": "Нужен файл в поле file (multipart/form-data)"}, status=400
            )
        try:
            article_file = add_article_file(
                context=request.tenant_context,
                article=article,
                upload=upload,
                author=request.user,
            )
        except ValidationError as error:
            return validation_response(error)
        return Response({"file": article_file_payload(article_file)}, status=201)


class ArticleFileDetailView(PortalBaseView):
    def delete(
        self, request: Request, portal_id: int, article_id: int, file_id: int
    ) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": "Портал не найден"}, status=404)
        article = _article(portal, article_id)
        if article is None:
            return Response({"detail": "Статья не найдена"}, status=404)
        article_file = article.files.filter(id=file_id).first()
        if article_file is None:
            return Response({"detail": "Файл не найден"}, status=404)
        try:
            delete_article_file(
                context=request.tenant_context, article_file=article_file
            )
        except ValidationError as error:
            return validation_response(error)
        return Response(status=204)
