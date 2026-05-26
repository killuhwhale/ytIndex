from django.core.management.base import BaseCommand

from apps.videos.models import IngestBatch, IngestJob
from apps.videos.tasks import ingest_job


class Command(BaseCommand):
    help = "Create and run an ingest job for a YouTube URL."

    def add_arguments(self, parser):
        parser.add_argument("url")
        parser.add_argument("--manual-transcript", default="")
        parser.add_argument("--owned-content", action="store_true")

    def handle(self, *args, **options):
        batch = IngestBatch.objects.create(input_text=options["url"], input_type=IngestBatch.InputType.SINGLE_URL, status=IngestBatch.Status.RUNNING, total_count=1)
        job = IngestJob.objects.create(batch=batch, source_url=options["url"])
        context = {"owned_content": options["owned_content"]}
        if options["manual_transcript"]:
            context["manual_transcript"] = options["manual_transcript"]
        ingest_job.delay(str(job.id), context)
        self.stdout.write(self.style.SUCCESS(f"Created batch {batch.id} job {job.id}"))
