from django.core.management.base import BaseCommand, CommandError

from hub_platform.subscriptions.plan_publish_service import (
    publish_saleable_plan_versions,
)


class Command(BaseCommand):
    help = (
        "Publishes the current draft PlanVersion for each saleable plan (Free, "
        "Startup). Once published a version and its grants are immutable; this "
        "is an irreversible production state change."
    )

    def handle(self, *args: object, **options: object) -> None:
        try:
            results = publish_saleable_plan_versions()
        except Exception as error:
            raise CommandError(f"Failed to publish plan versions: {error}") from error
        for result in results:
            state = "already published" if result.already_published else "published"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{result.plan_code}: {state} (publicId={result.public_id})"
                )
            )
