import asyncio

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the Grave Care Telegram Bot (polling mode)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Grave Care Telegram Bot..."))
        try:
            from bot_main import main
            asyncio.run(main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Bot stopped by user."))
