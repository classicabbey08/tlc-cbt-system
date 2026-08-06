from django.core.management.base import BaseCommand
from accounts.models import User


STUDENTS = [
    # JSS1
    ("Taiwo", "Anuoluwapo", "JSS1", "TLC/JSS1/001"),
    ("Anosike", "Neymar", "JSS1", "TLC/JSS1/002"),
    ("Bello", "Sofiat", "JSS1", "TLC/JSS1/003"),
    ("Muritala", "Islamiyah", "JSS1", "TLC/JSS1/004"),
    ("Olonimoyo", "Olamilekan", "JSS1", "TLC/JSS1/005"),

    # JSS2
    ("Adelani", "Ajoke", "JSS2", "TLC/JSS2/001"),
    ("Agada", "Esther", "JSS2", "TLC/JSS2/002"),
    ("Ifesanya", "Praise", "JSS2", "TLC/JSS2/003"),
    ("Umar", "Seyi", "JSS2", "TLC/JSS2/004"),
    ("Oluwadamilare", "Desire", "JSS2", "TLC/JSS2/005"),
    ("Salami", "Maleek", "JSS2", "TLC/JSS2/006"),

    # JSS3
    ("Amehin", "Success", "JSS3", "TLC/JSS3/001"),
    ("Oyenuga", "Anuoluwapo", "JSS3", "TLC/JSS3/002"),
    ("Okegbemi", "Fadilullah", "JSS3", "TLC/JSS3/003"),
    ("Adisa", "Amirat", "JSS3", "TLC/JSS3/004"),
    ("Bello", "Sahadat", "JSS3", "TLC/JSS3/005"),

    # SSS1
    ("Olusegun", "Eniola", "SSS1", "TLC/SSS1/001"),
    ("Oni", "Mustapha", "SSS1", "TLC/SSS1/002"),
    ("Adisa", "Aliat", "SSS1", "TLC/SSS1/003"),
    ("Agada", "Gloria", "SSS1", "TLC/SSS1/004"),
    ("Wilson", "David", "SSS1", "TLC/SSS1/005"),

    # SSS2
    ("Mulero", "Sesi", "SSS2", "TLC/SSS2/001"),
    ("Taiwo", "Tobiloba", "SSS2", "TLC/SSS2/002"),
    ("Oyenuga", "Emmanuel", "SSS2", "TLC/SSS2/003"),

    # SSS3
    ("Jaiyeola", "Lateefah", "SSS3", "TLC/SSS3/001"),
    ("Okegbemi", "Faridat", "SSS3", "TLC/SSS3/002"),
    ("Orija", "Opeyemi", "SSS3", "TLC/SSS3/003"),
    ("Olajide", "Oluwakemisola", "SSS3", "TLC/SSS3/004"),
    ("Hassan", "Oluwaseun", "SSS3", "TLC/SSS3/005"),
]


class Command(BaseCommand):
    help = "Seed all TLC students with default PIN 1234"

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for first, last, klass, adm in STUDENTS:
            # Username = admission number with slashes replaced
            username = adm.replace("/", "_").lower()  # e.g. tlc_jss1_001

            user, created = User.objects.get_or_create(
                admission_number=adm,
                defaults={
                    "username": username,
                    "first_name": first,
                    "last_name": last,
                    "role": User.Role.STUDENT,
                    "student_class": klass,
                },
            )

            if created:
                user.set_password("1234")
                user.save()
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {adm} – {first} {last}"))
            else:
                # Update existing record
                user.username = username
                user.first_name = first
                user.last_name = last
                user.role = User.Role.STUDENT
                user.student_class = klass
                user.set_password("1234")
                user.save()
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"Updated: {adm} – {first} {last}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Created: {created_count}, Updated: {updated_count}"
        ))