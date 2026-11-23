from django.urls import path

from chatballs.identity import (
    employee_invitations,
    employee_security_views,
    employee_update_views,
    employee_views,
    ownership_views,
    work_status_views,
)

urlpatterns = [
    path("<int:user_id>/dismiss/", employee_security_views.EmployeeDismissView.as_view(), name="employee-dismiss"),
    path("me/work-status/", work_status_views.OwnWorkStatusView.as_view(), name="own-work-status"),
    path("me/work-status/history/", work_status_views.WorkStatusHistoryView.as_view(), name="own-work-status-history"),
    path("<int:user_id>/work-status/", work_status_views.EmployeeWorkStatusView.as_view(), name="employee-work-status"),
    path("<int:user_id>/work-status/history/", work_status_views.WorkStatusHistoryView.as_view(), name="employee-work-status-history"),
    path("", employee_views.EmployeeListView.as_view(), name="employee-list"),
    # Создание сотрудника (ADMIN/EMPLOYEE по policy). Путь operators/ сохранён для
    # обратной совместимости; поле role в теле выбирает системную роль.
    path("operators/", employee_views.EmployeeCreateView.as_view(), name="employee-create"),
    # Ожидающие приглашения существующих учётных записей (статус «Приглашён»).
    path("invitations/<int:invitation_id>/resend/", employee_invitations.InvitationResendView.as_view(), name="employee-invitation-resend"),
    path("invitations/<int:invitation_id>/revoke/", employee_invitations.InvitationRevokeView.as_view(), name="employee-invitation-revoke"),
    path("<int:user_id>/", employee_views.EmployeeDetailView.as_view(), name="employee-detail"),
    path("<int:user_id>/avatar/", employee_views.EmployeeAvatarView.as_view(), name="employee-avatar"),
    path("<int:user_id>/update/", employee_update_views.EmployeeUpdateView.as_view(), name="employee-update"),
    path("<int:user_id>/reset-password/", employee_security_views.EmployeeResetPasswordView.as_view(), name="employee-reset-password"),
    path("<int:user_id>/revoke-sessions/", employee_security_views.EmployeeRevokeSessionsView.as_view(), name="employee-revoke-sessions"),
    path("<int:user_id>/block/", employee_security_views.EmployeeBlockView.as_view(), name="employee-block"),
    path("<int:user_id>/unblock/", employee_security_views.EmployeeUnblockView.as_view(), name="employee-unblock"),
    path("<int:user_id>/transfer-ownership/", ownership_views.OwnershipTransferView.as_view(), name="employee-transfer-ownership"),
]
