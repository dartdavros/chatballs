from django.urls import path

from hub_platform.identity import (
    employee_security_views,
    employee_views,
    ownership_views,
)

urlpatterns = [
    path("", employee_views.EmployeeListView.as_view(), name="employee-list"),
    # Создание сотрудника (ADMIN/EMPLOYEE по policy). Путь operators/ сохранён для
    # обратной совместимости; поле role в теле выбирает системную роль.
    path("operators/", employee_views.EmployeeCreateView.as_view(), name="employee-create"),
    path("<int:user_id>/", employee_views.EmployeeDetailView.as_view(), name="employee-detail"),
    path("<int:user_id>/avatar/", employee_views.EmployeeAvatarView.as_view(), name="employee-avatar"),
    path("<int:user_id>/update/", employee_views.EmployeeUpdateView.as_view(), name="employee-update"),
    path("<int:user_id>/reset-password/", employee_security_views.EmployeeResetPasswordView.as_view(), name="employee-reset-password"),
    path("<int:user_id>/revoke-sessions/", employee_security_views.EmployeeRevokeSessionsView.as_view(), name="employee-revoke-sessions"),
    path("<int:user_id>/block/", employee_security_views.EmployeeBlockView.as_view(), name="employee-block"),
    path("<int:user_id>/unblock/", employee_security_views.EmployeeUnblockView.as_view(), name="employee-unblock"),
    path("<int:user_id>/transfer-ownership/", ownership_views.OwnershipTransferView.as_view(), name="employee-transfer-ownership"),
]
