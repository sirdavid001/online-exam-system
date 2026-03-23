from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Initialize essential user groups (STUDENT, TEACHER)'

    def handle(self, *args, **options):
        groups = ['STUDENT', 'TEACHER']
        for name in groups:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created group: "{name}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Group "{name}" already exists.'))
