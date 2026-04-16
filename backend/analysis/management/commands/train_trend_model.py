"""Train and persist hybrid trend forecasting artifact."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from analysis.trend_model import (
    TrendModelError,
    default_trend_model_path,
    train_and_save_trend_model,
)


class Command(BaseCommand):
    help = "Train trend model (Prophet + LSTM-proxy fallback) for /api/trends/jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(default_trend_model_path()),
            help="Output pickle path for trend model artifact.",
        )
        parser.add_argument(
            "--max-jobs",
            type=int,
            default=50000,
            help="Maximum jobs for monthly trend series build (default: 50000).",
        )
        parser.add_argument(
            "--lookback",
            type=int,
            default=4,
            help="Lookback window for AR/LSTM-proxy branch (default: 4).",
        )
        parser.add_argument(
            "--min-points",
            type=int,
            default=6,
            help="Preferred minimum monthly points for full-quality training (default: 6).",
        )

    def handle(self, *args, **options):
        output = Path(options["output"]).expanduser().resolve()
        max_jobs = max(100, int(options["max_jobs"]))
        lookback = max(2, int(options["lookback"]))
        min_points = max(1, int(options["min_points"]))

        try:
            artifact = train_and_save_trend_model(
                output_path=output,
                max_jobs=max_jobs,
                lookback=lookback,
                min_points=min_points,
            )
        except TrendModelError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f"Trend model training failed: {exc}") from exc

        metrics = artifact.get("metrics", {})
        self.stdout.write(
            self.style.SUCCESS(
                "Trend model trained successfully. "
                f"samples={metrics.get('sample_count')}, "
                f"degraded={metrics.get('degraded_training')}, "
                f"residual_std={metrics.get('residual_std')}, "
                f"prophet_available={artifact.get('prophet_available')}, "
                f"saved_to={artifact.get('saved_to')}"
            )
        )
