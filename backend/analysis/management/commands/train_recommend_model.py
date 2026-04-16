"""Train and persist hybrid recommendation model artifact."""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from analysis.recommender import RecommenderError, default_model_path, retrain_and_save


class Command(BaseCommand):
    help = "Train TF-IDF + CF + LightFM (or SVD fallback) recommendation model."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=str(default_model_path()),
            help="Output pickle path for trained model artifact.",
        )
        parser.add_argument(
            "--max-jobs",
            type=int,
            default=10000,
            help="Maximum number of latest jobs for training (default: 10000).",
        )
        parser.add_argument("--alpha-cbf", type=float, default=0.5, help="CBF weight (default: 0.5).")
        parser.add_argument("--alpha-cf", type=float, default=0.3, help="CF weight (default: 0.3).")
        parser.add_argument("--alpha-lfm", type=float, default=0.2, help="LightFM/SVD weight (default: 0.2).")

    def handle(self, *args, **options):
        output = Path(options["output"]).expanduser().resolve()
        max_jobs = max(1, int(options["max_jobs"]))
        alpha_cbf = float(options["alpha_cbf"])
        alpha_cf = float(options["alpha_cf"])
        alpha_lfm = float(options["alpha_lfm"])

        try:
            artifact = retrain_and_save(
                output_path=output,
                max_jobs=max_jobs,
                alpha_cbf=alpha_cbf,
                alpha_cf=alpha_cf,
                alpha_lfm=alpha_lfm,
            )
        except RecommenderError as exc:
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(f"Training failed: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Recommendation model trained successfully. "
                f"jobs={len(artifact.get('job_ids', []))}, "
                f"users={len(artifact.get('user_ids', []))}, "
                f"backend={artifact.get('lfm_backend')}, "
                f"saved_to={artifact.get('saved_to')}"
            )
        )
