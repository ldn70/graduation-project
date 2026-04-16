"""Train and persist XGBoost salary model artifact."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from analysis.salary_model import (
    SalaryModelError,
    default_salary_model_path,
    train_and_save_salary_model,
)


class Command(BaseCommand):
    help = "Train XGBoost salary prediction model with SHAP-ready features."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(default_salary_model_path()),
            help="Output pickle path for salary model artifact.",
        )
        parser.add_argument(
            "--max-jobs",
            type=int,
            default=20000,
            help="Maximum number of jobs for training data build (default: 20000).",
        )
        parser.add_argument(
            "--min-samples",
            type=int,
            default=3,
            help="Minimum valid salary samples required for training (default: 3).",
        )

    def handle(self, *args, **options):
        output = Path(options["output"]).expanduser().resolve()
        max_jobs = max(100, int(options["max_jobs"]))
        min_samples = max(1, int(options["min_samples"]))
        try:
            artifact = train_and_save_salary_model(
                output_path=output,
                max_jobs=max_jobs,
                min_samples=min_samples,
            )
        except SalaryModelError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f"Salary model training failed: {exc}") from exc

        metrics = artifact.get("metrics", {})
        self.stdout.write(
            self.style.SUCCESS(
                "Salary model trained successfully. "
                f"samples={metrics.get('sample_count')}, "
                f"rmse={metrics.get('rmse')}, "
                f"saved_to={artifact.get('saved_to')}"
            )
        )
