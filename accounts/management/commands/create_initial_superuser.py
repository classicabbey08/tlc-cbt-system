from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings


class Command(BaseCommand):
    help = "Create the initial production Teacher if it does not exist."

    def handle(self, *args, **options):
        User = get_user_model()

        username = getattr(
            settings,
            "INITIAL_TEACHER_USERNAME",
            ""
        ).strip()

        email = getattr(
            settings,
            "INITIAL_TEACHER_EMAIL",
            ""
        ).strip()

        first_name = getattr(
            settings,
            "INITIAL_TEACHER_FIRST_NAME",
            "Teacher"
        ).strip()

        last_name = getattr(
            settings,
            "INITIAL_TEACHER_LAST_NAME",
            ""
        ).strip()

        password = getattr(
            settings,
            "INITIAL_TEACHER_PASSWORD",
            ""
        )

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Initial Teacher credentials are not configured. "
                    "Skipping creation."
                )
            )
            return

        user = User.objects.filter(username=username).first()

        if user:
            changed = False

            if user.role != User.Role.TEACHER:
                user.role = User.Role.TEACHER
                changed = True

            if first_name and user.first_name != first_name:
                user.first_name = first_name
                changed = True

            if last_name and user.last_name != last_name:
                user.last_name = last_name
                changed = True

            if email and user.email != email:
                user.email = email
                changed = True

            if changed:
                user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Teacher '{username}' already exists. "
                    f"Role verified as TEACHER."
                )
            )
            return

        user = User.objects.create_user(
            username=username,
            email=email or "",
            password=password,
            first_name=first_name,
            last_name=last_name,
        )

        user.role = User.Role.TEACHER
        user.is_staff = False
        user.is_superuser = False
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Initial Teacher '{user.username}' created successfully."
            )
        )