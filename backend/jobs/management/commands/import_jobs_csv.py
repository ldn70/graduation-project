"""Import job records from CSV into the jobs table."""

from __future__ import annotations

import csv
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from jobs.models import Job
from jobs.utils import clean_text, first_not_empty, normalize_education, parse_publish_time


FIELD_ALIASES = {
    "title": ["title", "职位名称", "岗位名称", "job_title"],
    "company": ["company", "公司名称", "企业名称"],
    "salary": ["salary", "薪资", "薪资范围", "salary_range"],
    "education": ["education", "学历", "学历要求"],
    "experience": ["experience", "经验", "工作经验", "经验要求"],
    "skills_required": ["skills_required", "skills", "技能", "技能要求", "skill_requirements"],
    "description": ["description", "职位描述", "岗位描述", "job_desc"],
    "location": ["location", "地区", "工作地点", "城市", "city"],
    "industry": ["industry", "行业", "行业类别"],
    "publish_time": ["publish_time", "发布时间", "发布日期", "date"],
    "job_url": ["job_url", "url", "链接", "职位链接"],
}


class Command(BaseCommand):
    help = "Import jobs from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to CSV file.")
        parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding (default: utf-8-sig)")
        parser.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
        parser.add_argument("--truncate", action="store_true", help="Delete existing jobs before import.")
        parser.add_argument("--limit", type=int, default=0, help="Import only first N rows (0 means all).")
        parser.add_argument(
            "--sync-mongo",
            action="store_true",
            help="Also sync imported records into MongoDB job_texts collection.",
        )
        parser.add_argument(
            "--mongo-uri",
            default=os.getenv("MONGO_URI", ""),
            help="MongoDB URI. Defaults to MONGO_URI env.",
        )
        parser.add_argument(
            "--mongo-db",
            default=os.getenv("MONGO_DB", "graduation_project"),
            help="MongoDB database name. Defaults to MONGO_DB or graduation_project.",
        )
        parser.add_argument(
            "--mongo-collection",
            default=os.getenv("MONGO_JOB_TEXTS_COLLECTION", "job_texts"),
            help="MongoDB collection name. Defaults to MONGO_JOB_TEXTS_COLLECTION or job_texts.",
        )
        parser.add_argument(
            "--mongo-timeout-ms",
            type=int,
            default=int(os.getenv("MONGO_TIMEOUT_MS", "3000")),
            help="MongoDB server selection timeout in ms. Defaults to MONGO_TIMEOUT_MS or 3000.",
        )
        parser.add_argument(
            "--mongo-truncate",
            action="store_true",
            help="When used with --sync-mongo, clear target Mongo collection before importing.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"]).expanduser().resolve()
        if not file_path.exists():
            raise CommandError(f"CSV file not found: {file_path}")

        encoding = options["encoding"]
        delimiter = options["delimiter"]
        truncate = options["truncate"]
        limit = options["limit"]
        sync_mongo = options["sync_mongo"]
        mongo_truncate = options["mongo_truncate"]

        if truncate:
            deleted, _ = Job.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Truncated existing jobs. Deleted rows: {deleted}"))

        mongo_client = None
        mongo_collection = None
        mongo_update_one = None
        mongo_synced = 0

        if sync_mongo:
            mongo_client, mongo_collection, mongo_update_one = self._init_mongo(options)
            if mongo_truncate:
                deleted_docs = mongo_collection.delete_many({}).deleted_count
                self.stdout.write(self.style.WARNING(f"Truncated Mongo collection. Deleted docs: {deleted_docs}"))

        imported = 0
        skipped = 0
        seen_urls = set(
            Job.objects.exclude(job_url__isnull=True).exclude(job_url__exact="").values_list("job_url", flat=True)
        )
        to_create = []

        try:
            with file_path.open("r", encoding=encoding, newline="") as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                if not reader.fieldnames:
                    raise CommandError("CSV header is empty.")

                for row in reader:
                    if limit and imported >= limit:
                        break
                    item = self._parse_row(row)
                    if not item["title"] or not item["company"]:
                        skipped += 1
                        continue

                    if item["job_url"] and item["job_url"] in seen_urls:
                        skipped += 1
                        continue
                    if item["job_url"]:
                        seen_urls.add(item["job_url"])

                    to_create.append(Job(**item))
                    imported += 1

                    if len(to_create) >= 1000:
                        created = Job.objects.bulk_create(to_create, batch_size=1000)
                        if sync_mongo and mongo_collection is not None and mongo_update_one is not None:
                            mongo_synced += self._sync_batch_to_mongo(
                                created if created else to_create,
                                mongo_collection,
                                mongo_update_one,
                            )
                        to_create.clear()
                        self.stdout.write(f"Imported rows: {imported}")

                if to_create:
                    created = Job.objects.bulk_create(to_create, batch_size=1000)
                    if sync_mongo and mongo_collection is not None and mongo_update_one is not None:
                        mongo_synced += self._sync_batch_to_mongo(
                            created if created else to_create,
                            mongo_collection,
                            mongo_update_one,
                        )

            summary = f"Import finished. Created: {imported}, skipped: {skipped}, source: {file_path.name}"
            if sync_mongo:
                summary += f", mongo_upserts: {mongo_synced}"

            self.stdout.write(
                self.style.SUCCESS(summary)
            )
        finally:
            if mongo_client is not None:
                mongo_client.close()

    def _pick(self, row: dict, key: str) -> str:
        aliases = FIELD_ALIASES[key]
        return first_not_empty(row.get(alias, "") for alias in aliases)

    def _parse_row(self, row: dict) -> dict:
        publish_time = parse_publish_time(self._pick(row, "publish_time")) or timezone.now()
        return {
            "title": clean_text(self._pick(row, "title"))[:100],
            "company": clean_text(self._pick(row, "company"))[:100],
            "salary": clean_text(self._pick(row, "salary"))[:50],
            "education": normalize_education(self._pick(row, "education"))[:50],
            "experience": clean_text(self._pick(row, "experience"))[:50],
            "skills_required": clean_text(self._pick(row, "skills_required")),
            "description": clean_text(self._pick(row, "description")),
            "location": clean_text(self._pick(row, "location"))[:100],
            "industry": clean_text(self._pick(row, "industry"))[:50],
            "publish_time": publish_time,
            "job_url": clean_text(self._pick(row, "job_url"))[:255],
        }

    def _init_mongo(self, options):
        mongo_uri = options["mongo_uri"].strip()
        mongo_db_name = options["mongo_db"].strip()
        mongo_collection_name = options["mongo_collection"].strip()
        mongo_timeout_ms = options["mongo_timeout_ms"]

        if not mongo_uri:
            raise CommandError("MongoDB sync requested but --mongo-uri (or MONGO_URI) is empty.")

        if not mongo_db_name:
            raise CommandError("MongoDB sync requested but --mongo-db is empty.")
        if not mongo_collection_name:
            raise CommandError("MongoDB sync requested but --mongo-collection is empty.")

        try:
            from pymongo import MongoClient, UpdateOne
        except ImportError as exc:
            raise CommandError(
                "pymongo is required for --sync-mongo. Please install dependencies from requirements.txt."
            ) from exc

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=mongo_timeout_ms)
        try:
            client.admin.command("ping")
        except Exception as exc:
            client.close()
            raise CommandError(f"Cannot connect to MongoDB: {exc}") from exc

        collection = client[mongo_db_name][mongo_collection_name]
        return client, collection, UpdateOne

    def _sync_batch_to_mongo(self, jobs: list[Job], collection, update_one_cls) -> int:
        if not jobs:
            return 0

        now = timezone.now()
        operations = []
        for job in jobs:
            filter_doc = self._mongo_filter_for_job(job)
            update_doc = {
                "$set": {
                    "job_id": job.id,
                    "job_url": job.job_url or "",
                    "title": job.title or "",
                    "company": job.company or "",
                    "industry": job.industry or "",
                    "location": job.location or "",
                    "publish_time": job.publish_time,
                    "desc_clean": job.description or "",
                    "extra_tags": self._build_extra_tags(job),
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": now,
                },
            }
            operations.append(update_one_cls(filter_doc, update_doc, upsert=True))

        try:
            result = collection.bulk_write(operations, ordered=False)
        except Exception as exc:
            raise CommandError(f"MongoDB bulk sync failed: {exc}") from exc

        return int((result.upserted_count or 0) + (result.modified_count or 0))

    def _mongo_filter_for_job(self, job: Job) -> dict:
        if job.job_url:
            return {"job_url": job.job_url}
        if job.id is not None:
            return {"job_id": job.id}

        # Fallback key when the backend does not return IDs after bulk create.
        return {
            "title": job.title or "",
            "company": job.company or "",
            "publish_time": job.publish_time,
        }

    def _build_extra_tags(self, job: Job) -> list[str]:
        tags: list[str] = []
        for field_value in (job.skills_required, job.education, job.experience):
            if field_value:
                text = clean_text(field_value)
                if text:
                    tags.append(text)
        return tags
