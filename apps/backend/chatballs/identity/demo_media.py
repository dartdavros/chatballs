"""Read only packaged demonstration avatars, without installing demonstration data."""

import mimetypes

from django.http import Http404

from chatballs.identity.demo_seed import manifest


def open_avatar(name):
    root = (manifest.MEDIA_DIR / "avatars").resolve()
    candidate = (root / name).resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise Http404("Demo media not found")
    content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    return candidate.open("rb"), content_type
