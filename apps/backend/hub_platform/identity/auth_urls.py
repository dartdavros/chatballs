from django.urls import path

from hub_platform.identity import auth_views

urlpatterns = [
    path("session/", auth_views.session_view, name="auth-session"),
    path("login/", auth_views.login_view, name="auth-login"),
    path("logout/", auth_views.logout_view, name="auth-logout"),
    path("password-reset/request/", auth_views.password_reset_request_view, name="auth-password-reset-request"),
    path("password-reset/validate/", auth_views.password_reset_validate_view, name="auth-password-reset-validate"),
    path("password-reset/confirm/", auth_views.password_reset_confirm_view, name="auth-password-reset-confirm"),
    path("profile/update/", auth_views.profile_update_view, name="auth-profile-update"),
    path("profile/password/", auth_views.profile_password_view, name="auth-profile-password"),
    path("profile/totp/start/", auth_views.profile_totp_start_view, name="auth-profile-totp-start"),
    path("profile/totp/disable/", auth_views.profile_totp_disable_view, name="auth-profile-totp-disable"),
    path("profile/sessions/revoke-other/", auth_views.profile_revoke_other_sessions_view, name="auth-profile-revoke-other-sessions"),
    path("change-temporary-password/", auth_views.change_temporary_password_view, name="auth-change-temp-password"),
    path("totp/setup/", auth_views.totp_setup_view, name="auth-totp-setup"),
    path("totp/confirm/", auth_views.totp_confirm_view, name="auth-totp-confirm"),
    path("totp/verify/", auth_views.totp_verify_view, name="auth-totp-verify"),
]
