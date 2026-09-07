from django.contrib import admin

from chatballs.support_portals.models import (
    PortalArticle,
    PortalArticleFeedback,
    PortalArticleRevision,
    PortalCategory,
    SupportPortal,
)


admin.site.register(
    (
        SupportPortal,
        PortalCategory,
        PortalArticle,
        PortalArticleRevision,
        PortalArticleFeedback,
    )
)
