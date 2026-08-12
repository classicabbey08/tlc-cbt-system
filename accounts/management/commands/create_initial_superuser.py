from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings


class Command(BaseCommand):
    help = "Create the initial production Super Admin if it does not exist."

    def handle(self, *args, **options):
        User = get_user_model()

        username = getattr(settings, "INITIAL_SUPERUSER_USERNAME", "").strip()
        email = getattr(settings, "INITIAL_SUPERUSER_EMAIL", "").strip()
        password = getattr(settings, "INITIAL_SUPERUSER_PASSWORD", "")

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Initial Super Admin credentials are not configured. "
                    "Skipping creation."
                )
            )
            return

        user = User.objects.filter(username=username).first()

        if user:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Super Admin '{username}' already exists. Nothing to do."
                )
            )
            return

        user = User.objects.create_superuser(
            username=username,
            email=email or None,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Initial Super Admin '{user.username}' created successfully."
            )
        )