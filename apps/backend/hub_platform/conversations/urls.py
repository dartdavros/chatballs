from django.urls import path

from hub_platform.conversations import chat_extras_views, reporting_views, views, voice_views

urlpatterns = [
    path("", views.ConversationListView.as_view(), name="conversation-list"),
    path("stats/", reporting_views.ConversationStatsView.as_view(), name="conversation-stats"),
    path("clients/", reporting_views.ClientsView.as_view(), name="conversation-clients"),
    path("clients/<int:contact_id>/", reporting_views.ClientDetailView.as_view(), name="conversation-client-detail"),
    path("<int:conversation_id>/", views.ConversationDetailView.as_view(), name="conversation-detail"),
    path("<int:conversation_id>/claim/", views.ConversationClaimView.as_view(), name="conversation-claim"),
    path("<int:conversation_id>/release/", views.ConversationReleaseView.as_view(), name="conversation-release"),
    path("<int:conversation_id>/return-queue/", views.ConversationReturnQueueView.as_view(), name="conversation-return-queue"),
    path("<int:conversation_id>/messages/", views.ConversationMessageView.as_view(), name="conversation-messages"),
    path("<int:conversation_id>/request-contact/", views.ConversationRequestContactView.as_view(), name="conversation-request-contact"),
    path("<int:conversation_id>/close/", views.ConversationCloseView.as_view(), name="conversation-close"),
    path("<int:conversation_id>/spam/", views.ConversationSpamView.as_view(), name="conversation-spam"),
    path("<int:conversation_id>/group/", views.ConversationGroupView.as_view(), name="conversation-group"),
    path("<int:conversation_id>/assignee/", views.ConversationAssigneeView.as_view(), name="conversation-assignee"),
    path("<int:conversation_id>/priority/", chat_extras_views.ConversationPriorityView.as_view(), name="conversation-priority"),
    path("<int:conversation_id>/note/", chat_extras_views.ConversationNoteView.as_view(), name="conversation-note"),
    path("<int:conversation_id>/labels/", chat_extras_views.ConversationLabelsView.as_view(), name="conversation-labels"),
    path("<int:conversation_id>/archive/", chat_extras_views.ConversationArchiveView.as_view(), name="conversation-archive"),
    path("counters/", chat_extras_views.ConversationCountersView.as_view(), name="conversation-counters"),
    path("labels/", chat_extras_views.LabelListView.as_view(), name="conversation-label-list"),
    path("labels/<int:label_id>/", chat_extras_views.LabelDetailView.as_view(), name="conversation-label-detail"),
    path("templates/", chat_extras_views.ReplyTemplateListView.as_view(), name="reply-template-list"),
    path("templates/<int:template_id>/", chat_extras_views.ReplyTemplateDetailView.as_view(), name="reply-template-detail"),
    path("<int:conversation_id>/voice/", voice_views.ConversationVoiceView.as_view(), name="conversation-voice"),
    path("messages/<int:message_id>/audio/", voice_views.MessageAudioView.as_view(), name="message-audio"),
    path("messages/<int:message_id>/transcribe/", voice_views.MessageTranscribeView.as_view(), name="message-transcribe"),
]
