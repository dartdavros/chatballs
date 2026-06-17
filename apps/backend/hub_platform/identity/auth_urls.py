from django.urls import path

from hub_platform.identity import auth_views

urlpatterns = [
    path("session/", auth_views.session_view, name="auth-session"),
    path("login/", auth_views.login_view, name="auth-login"),
    path("logout/", auth_views.logout_view, name="auth-logout"),
    path("change-temporary-password/", auth_views.change_temporary_password_view, name="auth-change-temp-password"),
    path("totp/setup/", auth_views.totp_setup_view, name="auth-totp-setup"),
    path("totp/confirm/", auth_views.totp_confirm_view, name="auth-totp-confirm"),
    path("totp/verify/", auth_views.totp_verify_view, name="auth-totp-verify"),
]
