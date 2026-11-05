"""The existing bootstrap domain operation, separate from login/CSRF transport."""

from chatballs.identity.setup import SetupInput, complete_setup


def finish(body, *, public_host, public_scheme):
    body = body if isinstance(body, dict) else {}
    return complete_setup(SetupInput(
        organization_name=str(body.get("organizationName", "")),
        full_name=str(body.get("fullName", "")), email=str(body.get("email", "")),
        password=str(body.get("password", "")), install_demo=bool(body.get("installDemo", False)),
        language=str(body.get("language", ""))), public_host=public_host, public_scheme=public_scheme)
