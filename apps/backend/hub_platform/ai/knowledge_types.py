from django.db import models


UNCATEGORIZED_CATEGORY_NAME = "Без категории"


class KnowledgeVisibility(models.TextChoices):
    ORGANIZATION = "ORGANIZATION", "Organization"
    DEPARTMENTS = "DEPARTMENTS", "Departments"
