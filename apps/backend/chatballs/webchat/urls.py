from django.urls import path

from chatballs.webchat import views
from chatballs.webchat.asset_views import WidgetAssetView
from chatballs.webchat.author_avatar_views import WebchatAuthorAvatarView
from chatballs.webchat.config_views import WebchatConfigView
from chatballs.webchat.consent_views import WebchatConsentView
from chatballs.webchat.dictation_views import WebchatDictationView
from chatballs.webchat.observation_views import WebchatObservationsView
from chatballs.webchat.site_event_views import WebchatSiteEventCancelView, WebchatSiteEventView
from chatballs.webchat.synthesis_views import WebchatSynthesisView

urlpatterns = [
    path("assets/<uuid:public_id>/", WidgetAssetView.as_view(), name="webchat-asset"),
    path("config/", WebchatConfigView.as_view(), name="webchat-config"),
    path("session/", views.WebchatSessionView.as_view(), name="webchat-session"),
    path("consent/", WebchatConsentView.as_view(), name="webchat-consent"),
    path("dictation/", WebchatDictationView.as_view(), name="webchat-dictation"),
    path("messages/<int:message_id>/synthesis/", WebchatSynthesisView.as_view(), name="webchat-synthesis"),
    path("fields/", views.WebchatFieldsView.as_view(), name="webchat-fields"),
    path("site-events/", WebchatSiteEventView.as_view(), name="webchat-site-event"),
    path("site-events/cancel/", WebchatSiteEventCancelView.as_view(), name="webchat-site-event-cancel"),
    path("observations/", WebchatObservationsView.as_view(), name="webchat-observations"),
    path("messages/", views.WebchatMessagesView.as_view(), name="webchat-messages"),
    path("messages/<int:message_id>/author-avatar/", WebchatAuthorAvatarView.as_view(), name="webchat-author-avatar"),
    path("messages/<int:message_id>/audio/", views.WebchatMessageAudioView.as_view(), name="webchat-message-audio"),
    path("messages/<int:message_id>/attachment/", views.WebchatMessageAttachmentView.as_view(), name="webchat-message-attachment"),
    path("contact/", views.WebchatContactView.as_view(), name="webchat-contact"),
    path("call/open/", views.WebchatCallOpenView.as_view(), name="webchat-call-open"),
    path("call/decline/", views.WebchatCallDeclineView.as_view(), name="webchat-call-decline"),
]
