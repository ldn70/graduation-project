"""Import job records from CSV into the jobs table."""

from __future__ import annotations

import csv
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

    def handle(self, *args, **options):
        file_path = Path(options["file"]).expanduser().resolve()
        if not file_path.exists():
            raise CommandError(f"CSV file not found: {file_path}")

        encoding = options["encoding"]
        delimiter = options["delimiter"]
        truncate = options["truncate"]
        limit = options["limit"]

        if truncate:
            deleted, _ = Job.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Truncated existing jobs. Deleted rows: {deleted}"))

        imported = 0
        skipped = 0
        seen_urls = set(
            Job.objects.exclude(job_url__isnull=True).exclude(job_url__exact="").values_list("job_url", flat=True)
        )
        to_create = []

        with file_path.open("r", encoding=encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                raise CommandError("CSV header is empty.")

            for idx, row in enumerate(reader, start=1):
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
                    Job.objects.bulk_create(to_create, batch_size=1000)
                    to_create.clear()
                    self.stdout.write(f"Imported rows: {imported}")

            if to_create:
                Job.objects.bulk_create(to_create, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(
                f"Import finished. Created: {imported}, skipped: {skipped}, source: {file_path.name}"
            )
        )

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
