from django.core.management.base import BaseCommand

from chatballs.updates.check_in_state import reset_for_independent_copy


class Command(BaseCommand):
    help = "Assign a new identity to an independent copy and disable its external checks."

    def add_arguments(self, parser):
        parser.add_argument("--confirm-independent-copy", action="store_true", required=True)

    def handle(self, *args, **options):
        reset_for_independent_copy()
