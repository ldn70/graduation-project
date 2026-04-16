"""Trend forecasting helpers (Prophet + LSTM-proxy hybrid with fallback)."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
import math
import os
import pickle
from typing import Any, Iterable

from django.conf import settings

from jobs.models import Job


_MODEL_CACHE: dict[str, Any] = {}


class TrendModelError(Exception):
    """Raised when trend model training/inference fails."""


def _require_numpy():
    try:
        import numpy as np
    except Exception as exc:
        raise TrendModelError("numpy is required for trend modeling.") from exc
    return np


def _is_prophet_available() -> bool:
    try:
        from prophet import Prophet  # noqa: F401
    except Exception:
        return False
    return True


def default_trend_model_path() -> Path:
    configured = os.getenv("TREND_MODEL_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return (settings.BASE_DIR / "analysis" / "models" / "trend_hybrid.pkl").resolve()


def save_artifact(artifact: dict[str, Any], output_path: Path | str | None = None) -> Path:
    path = Path(output_path) if output_path else default_trend_model_path()
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(artifact, f)
    return path


def load_artifact(model_path: Path | str | None = None, use_cache: bool = True) -> dict[str, Any] | None:
    path = Path(model_path) if model_path else default_trend_model_path()
    path = path.expanduser().resolve()
    if not path.exists():
        return None

    mtime = path.stat().st_mtime
    cache_key = str(path)
    if use_cache:
        cached = _MODEL_CACHE.get(cache_key)
        if cached and cached.get("mtime") == mtime:
            return cached["artifact"]

    with path.open("rb") as f:
        artifact = pickle.load(f)
    _MODEL_CACHE[cache_key] = {"mtime": mtime, "artifact": artifact}
    return artifact


def _normalize_time_range(time_range: str | None) -> str:
    value = (time_range or "month").strip().lower()
    if value in {"month", "quarter", "year"}:
        return value
    return "month"


def _period_from_dt(dt: datetime, time_range: str):
    if time_range == "year":
        return (dt.year,)
    if time_range == "quarter":
        return (dt.year, (dt.month - 1) // 3 + 1)
    return (dt.year, dt.month)


def _period_to_label(period: tuple[int, ...], time_range: str) -> str:
    if time_range == "year":
        return f"{period[0]:04d}"
    if time_range == "quarter":
        return f"{period[0]:04d}-Q{period[1]}"
    return f"{period[0]:04d}-{period[1]:02d}"


def _next_period(period: tuple[int, ...], time_range: str):
    if time_range == "year":
        return (period[0] + 1,)
    if time_range == "quarter":
        year, quarter = period
        quarter += 1
        if quarter > 4:
            year += 1
            quarter = 1
        return (year, quarter)
    year, month = period
    month += 1
    if month > 12:
        year += 1
        month = 1
    return (year, month)


def _parse_label(label: str, time_range: str):
    if time_range == "year":
        return (int(label),)
    if time_range == "quarter":
        year, quarter = label.split("-Q")
        return (int(year), int(quarter))
    year, month = label.split("-")
    return (int(year), int(month))


def build_historical_series(
    jobs: Iterable[Job],
    time_range: str = "month",
    include_empty: bool = True,
) -> list[dict[str, Any]]:
    time_range = _normalize_time_range(time_range)

    counter = Counter()
    for job in jobs:
        ts = getattr(job, "publish_time", None)
        if not ts:
            continue
        counter[_period_from_dt(ts, time_range)] += 1

    if not counter:
        return []

    periods = sorted(counter.keys())
    if not include_empty:
        return [
            {"date": _period_to_label(period, time_range), "count": counter[period]}
            for period in periods
        ]

    current = periods[0]
    end = periods[-1]
    historical: list[dict[str, Any]] = []
    while current <= end:
        historical.append(
            {"date": _period_to_label(current, time_range), "count": int(counter.get(current, 0))}
        )
        current = _next_period(current, time_range)
    return historical


def baseline_forecast(
    historical: list[dict[str, Any]],
    time_range: str = "month",
    steps: int = 3,
) -> list[dict[str, Any]]:
    time_range = _normalize_time_range(time_range)
    steps = max(1, int(steps or 3))
    if not historical:
        return []

    counts = [float(item["count"]) for item in historical]
    if len(counts) >= 2:
        delta = counts[-1] - counts[-2]
        diffs = [counts[i] - counts[i - 1] for i in range(1, len(counts))]
        volatility = math.sqrt(sum(x * x for x in diffs) / len(diffs))
    else:
        delta = 0.0
        volatility = max(1.0, counts[-1] * 0.15)

    period = _parse_label(str(historical[-1]["date"]), time_range)
    last = counts[-1]
    output: list[dict[str, Any]] = []
    for _ in range(steps):
        period = _next_period(period, time_range)
        pred = max(0.0, last + delta)
        bound = max(1.0, volatility)
        output.append(
            {
                "date": _period_to_label(period, time_range),
                "count": round(pred, 2),
                "upper_bound": round(pred + 1.28 * bound, 2),
                "lower_bound": round(max(0.0, pred - 1.28 * bound), 2),
            }
        )
        last = pred
    return output


def _fit_ar_proxy(values, lookback: int):
    np = _require_numpy()
    lookback = max(2, int(lookback))
    if len(values) <= lookback:
        return [0.0] * lookback, float(values[-1]) if len(values) else 0.0

    x_rows = []
    y_rows = []
    for idx in range(lookback, len(values)):
        x_rows.append(values[idx - lookback : idx])
        y_rows.append(values[idx])
    X = np.asarray(x_rows, dtype=float)
    y = np.asarray(y_rows, dtype=float)

    X_bias = np.c_[X, np.ones(X.shape[0], dtype=float)]
    coef, _, _, _ = np.linalg.lstsq(X_bias, y, rcond=None)
    weights = coef[:-1].astype(float).tolist()
    bias = float(coef[-1])
    return weights, bias


def build_monthly_training_series(max_jobs: int = 50000) -> list[dict[str, Any]]:
    max_jobs = max(100, int(max_jobs))
    jobs = (
        Job.objects.exclude(publish_time__isnull=True)
        .order_by("publish_time", "id")
        .only("publish_time")[:max_jobs]
    )
    return build_historical_series(jobs, time_range="month", include_empty=True)


def train_and_save_trend_model(
    output_path: Path | str | None = None,
    max_jobs: int = 50000,
    lookback: int = 4,
    min_points: int = 6,
) -> dict[str, Any]:
    np = _require_numpy()
    historical = build_monthly_training_series(max_jobs=max_jobs)
    if not historical:
        raise TrendModelError("No valid publish_time samples for trend training.")
    min_points = max(1, int(min_points))
    degraded_training = len(historical) < min_points

    counts = np.asarray([float(item["count"]) for item in historical], dtype=float)
    x = np.arange(len(counts), dtype=float)

    if len(counts) >= 2:
        slope, intercept = np.polyfit(x, counts, 1)
    else:
        slope, intercept = 0.0, float(counts[-1])

    lookback = max(2, int(lookback))
    ar_weights, ar_bias = _fit_ar_proxy(counts, lookback=lookback)

    monthly_bucket: dict[str, list[float]] = {f"{i:02d}": [] for i in range(1, 13)}
    for point in historical:
        _, month = point["date"].split("-")
        monthly_bucket[month].append(float(point["count"]))
    mean_value = float(np.mean(counts)) if len(counts) else 1.0
    seasonal_factors = {}
    for month in sorted(monthly_bucket.keys()):
        month_values = monthly_bucket[month]
        if not month_values or mean_value <= 1e-8:
            seasonal_factors[month] = 1.0
        else:
            seasonal_factors[month] = max(0.4, min(1.8, float(np.mean(month_values) / mean_value)))

    pred_for_residual = []
    for idx in range(lookback, len(counts)):
        window = counts[idx - lookback : idx]
        pred = float(np.dot(window, np.asarray(ar_weights, dtype=float)) + ar_bias)
        pred_for_residual.append(pred)
    if pred_for_residual:
        residual = counts[lookback:] - np.asarray(pred_for_residual, dtype=float)
        residual_std = float(np.std(residual))
    else:
        residual_std = float(np.std(counts)) if len(counts) else 1.0

    artifact = {
        "model_version": 1,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "lookback": lookback,
        "ar_weights": ar_weights,
        "ar_bias": ar_bias,
        "trend_slope": float(slope),
        "trend_intercept": float(intercept),
        "seasonal_factors": seasonal_factors,
        "prophet_available": _is_prophet_available(),
        "metrics": {
            "sample_count": len(historical),
            "residual_std": round(max(0.5, residual_std), 4),
            "mean_count": round(float(np.mean(counts)), 4),
            "std_count": round(float(np.std(counts)), 4),
            "degraded_training": degraded_training,
        },
    }
    output = save_artifact(artifact, output_path=output_path)
    artifact["saved_to"] = str(output)
    return artifact


def _forecast_monthly_with_ar(
    historical: list[dict[str, Any]],
    horizon: int,
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    np = _require_numpy()
    horizon = max(1, int(horizon))
    counts = [float(item["count"]) for item in historical]
    lookback = max(2, int(artifact.get("lookback", 4)))
    weights = [float(x) for x in artifact.get("ar_weights", [])]
    if len(weights) != lookback:
        weights = [0.0] * lookback
    bias = float(artifact.get("ar_bias", counts[-1] if counts else 0.0))
    slope = float(artifact.get("trend_slope", 0.0))
    seasonal = artifact.get("seasonal_factors", {})

    std = float(artifact.get("metrics", {}).get("residual_std", max(1.0, np.std(counts) if counts else 1.0)))
    period = _parse_label(str(historical[-1]["date"]), "month")

    series = counts[:]
    output: list[dict[str, Any]] = []
    for _ in range(horizon):
        period = _next_period(period, "month")
        while len(series) < lookback:
            series.insert(0, series[0] if series else 0.0)
        window = np.asarray(series[-lookback:], dtype=float)
        pred = float(np.dot(window, np.asarray(weights, dtype=float)) + bias)
        pred += slope
        month_key = f"{period[1]:02d}"
        pred *= float(seasonal.get(month_key, 1.0))
        pred = max(0.0, pred)
        output.append(
            {
                "date": _period_to_label(period, "month"),
                "count": round(pred, 2),
                "upper_bound": round(pred + 1.28 * std, 2),
                "lower_bound": round(max(0.0, pred - 1.28 * std), 2),
            }
        )
        series.append(pred)
    return output


def _forecast_monthly_with_prophet(
    historical: list[dict[str, Any]],
    horizon: int,
) -> list[dict[str, Any]]:
    if len(historical) < 6:
        return []

    try:
        import pandas as pd
        from prophet import Prophet
    except Exception:
        return []

    try:
        df = pd.DataFrame(
            {
                "ds": [datetime.strptime(f"{row['date']}-01", "%Y-%m-%d") for row in historical],
                "y": [float(row["count"]) for row in historical],
            }
        )
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.08,
        )
        model.fit(df)
        future = model.make_future_dataframe(periods=max(1, int(horizon)), freq="MS")
        pred = model.predict(future).tail(max(1, int(horizon)))
    except Exception:
        return []

    output = []
    for _, row in pred.iterrows():
        count = max(0.0, float(row["yhat"]))
        output.append(
            {
                "date": row["ds"].strftime("%Y-%m"),
                "count": round(count, 2),
                "upper_bound": round(max(count, float(row["yhat_upper"])), 2),
                "lower_bound": round(max(0.0, min(count, float(row["yhat_lower"]))), 2),
            }
        )
    return output


def forecast_from_historical(
    historical: list[dict[str, Any]],
    time_range: str = "month",
    steps: int = 3,
    model_path: Path | str | None = None,
) -> dict[str, Any]:
    time_range = _normalize_time_range(time_range)
    steps = max(1, int(steps or 3))
    if not historical:
        return {"forecast": [], "model_info": {"backend": "none"}}

    if time_range != "month":
        return {
            "forecast": baseline_forecast(historical, time_range=time_range, steps=steps),
            "model_info": {"backend": "baseline", "time_range": time_range},
        }

    artifact = load_artifact(model_path=model_path, use_cache=True)
    if artifact is None:
        raise TrendModelError("Trend model is not trained yet.")

    ar_forecast = _forecast_monthly_with_ar(historical, horizon=steps, artifact=artifact)
    backends = ["ar_proxy"]
    forecast = ar_forecast

    prophet_forecast = []
    if artifact.get("prophet_available"):
        prophet_forecast = _forecast_monthly_with_prophet(historical, horizon=steps)

    if prophet_forecast and len(prophet_forecast) == len(ar_forecast):
        backends.append("prophet")
        fused = []
        for p_row, a_row in zip(prophet_forecast, ar_forecast):
            count = round(0.65 * float(p_row["count"]) + 0.35 * float(a_row["count"]), 2)
            fused.append(
                {
                    "date": p_row["date"],
                    "count": count,
                    "upper_bound": round(max(float(p_row["upper_bound"]), float(a_row["upper_bound"])), 2),
                    "lower_bound": round(min(float(p_row["lower_bound"]), float(a_row["lower_bound"])), 2),
                }
            )
        forecast = fused

    return {
        "forecast": forecast,
        "model_info": {
            "backend": "+".join(backends),
            "trained_at": artifact.get("trained_at"),
            "lookback": artifact.get("lookback"),
            "sample_count": artifact.get("metrics", {}).get("sample_count", 0),
            "prophet_available": bool(artifact.get("prophet_available")),
        },
    }
