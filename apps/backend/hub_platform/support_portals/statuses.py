from django.db import models


class PortalStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    PUBLISHED = "PUBLISHED", "Опубликован"
    ARCHIVED = "ARCHIVED", "Архив"


class ArticleStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    PUBLISHED = "PUBLISHED", "Опубликована"
    ARCHIVED = "ARCHIVED", "Архив"
