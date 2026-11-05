"""Диктовка не использует Django TemporaryFileUploadHandler."""

from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.uploadhandler import FileUploadHandler, StopFutureHandlers
from rest_framework.exceptions import ValidationError

from chatballs.i18n import t


class BoundedMemoryUploadHandler(FileUploadHandler):
    def __init__(self, request, max_bytes: int):
        super().__init__(request)
        self.max_bytes = max_bytes
        self.total = 0

    def new_file(self, *args, **kwargs):
        super().new_file(*args, **kwargs)
        self.file = BytesIO()
        raise StopFutureHandlers()

    def receive_data_chunk(self, raw_data, start):
        self.total += len(raw_data)
        if self.total > self.max_bytes:
            self.file.close()
            raise ValidationError({"detail": t("speech.too_large")})
        self.file.write(raw_data)

    def file_complete(self, file_size):
        self.file.seek(0)
        return InMemoryUploadedFile(
            self.file, self.field_name, self.file_name, self.content_type,
            file_size, self.charset, self.content_type_extra,
        )

    def upload_interrupted(self):
        if hasattr(self, "file"):
            self.file.close()
