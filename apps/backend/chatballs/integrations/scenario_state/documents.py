"""Encrypted JSON documents owned by a tenant, with no plaintext audit copy."""

import json

from django.db import models

from chatballs.identity.crypto import decrypt_secret, encrypt_secret
from chatballs.tenancy.models import TenantRelationModel


class EncryptedDocumentModel(TenantRelationModel):
    content = models.TextField()

    class Meta:
        abstract = True

    @property
    def definition(self):
        return json.loads(decrypt_secret(self.content))

    @definition.setter
    def definition(self, value):
        self.content = encrypt_secret(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
