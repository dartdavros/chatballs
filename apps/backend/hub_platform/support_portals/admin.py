from django.contrib import admin

from hub_platform.support_portals.models import (
    PortalArticle,
    PortalArticleFeedback,
    PortalArticleRevision,
    PortalCategory,
    SupportPortal,
    SupportPortalProduct,
)


admin.site.register(
    (
        SupportPortal,
        SupportPortalProduct,
        PortalCategory,
        PortalArticle,
        PortalArticleRevision,
        PortalArticleFeedback,
    )
)
