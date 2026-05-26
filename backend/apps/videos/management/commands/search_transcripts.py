from django.core.management.base import BaseCommand

from apps.videos.services.search import search_transcripts


class Command(BaseCommand):
    help = "Search indexed transcript chunks."

    def add_arguments(self, parser):
        parser.add_argument("query")
        parser.add_argument("--type", default="hybrid", choices=["keyword", "semantic", "hybrid"])

    def handle(self, *args, **options):
        for result in search_transcripts(options["query"], options["type"], limit=10):
            self.stdout.write(f"{result['score']} {result['title']} {result['youtube_timestamp_url']}")
            self.stdout.write(result["snippet"][:220])
