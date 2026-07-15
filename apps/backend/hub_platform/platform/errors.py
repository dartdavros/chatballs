from __future__ import annotations


class ProvisioningError(Exception):
    """Base class for provisioning domain errors. message is safe to expose."""

    status_code: int = 400

    def __init__(self, message: str, *, code: str = "") -> None:
        super().__init__(message)
        self.code = code


class ProvisioningConflict(ProvisioningError):
    status_code = 409


class ProvisioningValidation(ProvisioningError):
    status_code = 400


class ProvisioningOwnerUnavailable(ProvisioningError):
    status_code = 422
