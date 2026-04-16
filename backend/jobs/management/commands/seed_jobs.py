"""Seed demo jobs for local development."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from jobs.models import Job


class Command(BaseCommand):
    help = "Seed demo jobs for local development"

    def handle(self, *args, **options):
        samples = [
            {
                "title": "Python开发工程师",
                "company": "星辰科技",
                "salary": "15-25K",
                "education": "本科",
                "experience": "3-5年",
                "skills_required": "Python,Django,MySQL,RESTful",
                "description": "负责后端服务开发与优化",
                "location": "北京",
                "industry": "互联网",
                "job_url": "https://example.com/job/1",
            },
            {
                "title": "数据分析师",
                "company": "远望数据",
                "salary": "12-20K",
                "education": "本科",
                "experience": "1-3年",
                "skills_required": "SQL,Python,Tableau,统计学",
                "description": "负责业务数据分析与报表建设",
                "location": "上海",
                "industry": "互联网",
                "job_url": "https://example.com/job/2",
            },
            {
                "title": "Java开发工程师",
                "company": "凌云软件",
                "salary": "14-22K",
                "education": "本科",
                "experience": "3-5年",
                "skills_required": "Java,Spring,MySQL,Redis",
                "description": "负责核心业务服务设计与开发",
                "location": "成都",
                "industry": "软件",
                "job_url": "https://example.com/job/3",
            },
        ]

        created = 0
        for item in samples:
            _, is_created = Job.objects.get_or_create(
                title=item["title"],
                company=item["company"],
                defaults={**item, "publish_time": timezone.now()},
            )
            created += int(is_created)

        self.stdout.write(self.style.SUCCESS(f"Seed finished. Created {created} jobs."))
