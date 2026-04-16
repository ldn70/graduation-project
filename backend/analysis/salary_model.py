"""Salary prediction model helpers (XGBoost + SHAP)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import math
import os
import pickle
from typing import Any

from django.conf import settings

from jobs.models import Job
from jobs.utils import parse_experience_years, parse_salary_range_k_month, split_skills


_MODEL_CACHE: dict[str, Any] = {}


class SalaryModelError(Exception):
    """Raised when salary model training/inference fails."""


def _require_numpy():
    try:
        import numpy as np
    except Exception as exc:
        raise SalaryModelError("numpy is required for salary model.") from exc
    return np


def _require_xgboost():
    try:
        from xgboost import XGBRegressor
    except Exception as exc:
        raise SalaryModelError("xgboost is required for salary model training.") from exc
    return XGBRegressor


def _require_sklearn():
    try:
        from sklearn.feature_extraction import DictVectorizer  # noqa: F401
        from sklearn.metrics import mean_squared_error  # noqa: F401
    except Exception as exc:
        raise SalaryModelError("scikit-learn is required for salary model.") from exc


def default_salary_model_path() -> Path:
    configured = os.getenv("SALARY_MODEL_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return (settings.BASE_DIR / "analysis" / "models" / "salary_xgb.pkl").resolve()


def save_artifact(artifact: dict[str, Any], output_path: Path | str | None = None) -> Path:
    path = Path(output_path) if output_path else default_salary_model_path()
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(artifact, f)
    return path


def load_artifact(model_path: Path | str | None = None, use_cache: bool = True) -> dict[str, Any] | None:
    path = Path(model_path) if model_path else default_salary_model_path()
    path = path.expanduser().resolve()
    if not path.exists():
        return None

    mtime = path.stat().st_mtime
    key = str(path)
    if use_cache:
        cached = _MODEL_CACHE.get(key)
        if cached and cached.get("mtime") == mtime:
            return cached["artifact"]

    with path.open("rb") as f:
        artifact = pickle.load(f)
    _MODEL_CACHE[key] = {"mtime": mtime, "artifact": artifact}
    return artifact


def _normalize_city(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return "unknown"
    for sep in ("-", "/", "·", " "):
        if sep in value:
            value = value.split(sep)[0]
            break
    return value or "unknown"


def _feature_dict(
    *,
    job_title: str,
    education: str,
    experience: str,
    skills: list[str] | set[str] | tuple[str, ...] | str | None,
    city: str,
    industry: str,
) -> dict[str, Any]:
    if isinstance(skills, str):
        skill_set = split_skills(skills)
    else:
        skill_set = set()
        for item in skills or []:
            if item:
                skill_set.update(split_skills(str(item)))

    feat: dict[str, Any] = {
        "job_title": (job_title or "").strip() or "unknown",
        "education": (education or "").strip() or "unknown",
        "city": _normalize_city(city),
        "industry": (industry or "").strip() or "unknown",
        "experience_years": float(parse_experience_years(experience or "")),
        "skill_count": float(len(skill_set)),
    }
    for token in sorted(skill_set):
        feat[f"skill={token}"] = 1.0
    return feat


def build_training_dataset(max_jobs: int = 20000, min_samples: int = 3):
    _require_sklearn()
    np = _require_numpy()
    from sklearn.feature_extraction import DictVectorizer

    max_jobs = max(100, int(max_jobs))
    rows = list(
        Job.objects.exclude(salary__isnull=True)
        .exclude(salary__exact="")
        .order_by("-publish_time", "-id")[:max_jobs]
        .values(
            "title",
            "education",
            "experience",
            "skills_required",
            "location",
            "industry",
            "salary",
        )
    )

    feats: list[dict[str, Any]] = []
    y: list[float] = []
    for row in rows:
        low, high = parse_salary_range_k_month(row["salary"])
        if low is None or high is None:
            continue
        target = float((low + high) / 2.0)
        if target <= 0:
            continue
        feats.append(
            _feature_dict(
                job_title=row["title"] or "",
                education=row["education"] or "",
                experience=row["experience"] or "",
                skills=row["skills_required"] or "",
                city=row["location"] or "",
                industry=row["industry"] or "",
            )
        )
        y.append(target)

    if len(y) < max(1, int(min_samples)):
        raise SalaryModelError(f"Not enough training samples with valid salary ranges: {len(y)}")

    vectorizer = DictVectorizer(sparse=True)
    X = vectorizer.fit_transform(feats)
    return X, np.asarray(y, dtype=float), vectorizer


def train_and_save_salary_model(
    output_path: Path | str | None = None,
    max_jobs: int = 20000,
    min_samples: int = 3,
) -> dict[str, Any]:
    np = _require_numpy()
    _require_sklearn()
    XGBRegressor = _require_xgboost()
    from sklearn.metrics import mean_squared_error

    X, y, vectorizer = build_training_dataset(max_jobs=max_jobs, min_samples=min_samples)

    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=300,
        max_depth=6,
        learning_rate=0.06,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_alpha=0.0,
        reg_lambda=1.0,
        random_state=42,
    )
    model.fit(X, y)

    pred = model.predict(X)
    rmse = float(math.sqrt(mean_squared_error(y, pred)))
    residual = y - pred
    residual_std = float(np.std(residual))

    artifact = {
        "model_version": 1,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "model_type": "xgboost",
        "model": model,
        "vectorizer": vectorizer,
        "feature_names": list(vectorizer.get_feature_names_out()),
        "metrics": {
            "rmse": round(rmse, 4),
            "sample_count": int(len(y)),
            "mean_salary": round(float(np.mean(y)), 3),
            "std_salary": round(float(np.std(y)), 3),
            "residual_std": round(residual_std, 4),
        },
    }

    output = save_artifact(artifact, output_path=output_path)
    artifact["saved_to"] = str(output)
    return artifact


def _compute_shap_explanation(artifact: dict[str, Any], x_row, top_n: int = 8) -> list[dict[str, Any]]:
    np = _require_numpy()
    model = artifact["model"]
    feature_names = artifact.get("feature_names", [])

    try:
        import shap
    except Exception:
        return [
            {
                "feature": "explainability",
                "impact": 0.0,
                "note": "shap_not_installed",
            }
        ]

    try:
        dense = x_row.toarray()
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(dense)
        if isinstance(shap_values, list):
            shap_values = shap_values[0]
        row = np.asarray(shap_values[0], dtype=float)
    except Exception:
        return [
            {
                "feature": "explainability",
                "impact": 0.0,
                "note": "shap_compute_failed",
            }
        ]

    idx_sorted = np.argsort(np.abs(row))[::-1]
    output: list[dict[str, Any]] = []
    for idx in idx_sorted[: max(1, top_n)]:
        impact = float(row[int(idx)])
        if abs(impact) < 1e-8 and len(output) >= 3:
            continue
        raw_name = feature_names[int(idx)] if int(idx) < len(feature_names) else f"f{idx}"
        name = raw_name.replace("=", ":")
        output.append({"feature": name, "impact": round(impact, 4)})
    if output:
        return output
    return [{"feature": "model", "impact": 0.0}]


def predict_salary_from_payload(
    payload: dict[str, Any],
    model_path: Path | str | None = None,
) -> dict[str, Any]:
    artifact = load_artifact(model_path=model_path, use_cache=True)
    if artifact is None:
        raise SalaryModelError("Salary model is not trained yet.")

    vectorizer = artifact["vectorizer"]
    model = artifact["model"]
    metrics = artifact.get("metrics", {})

    feat = _feature_dict(
        job_title=str(payload.get("job_title", "")),
        education=str(payload.get("education", "")),
        experience=str(payload.get("experience", "")),
        skills=payload.get("skills", []),
        city=str(payload.get("city", "")),
        industry=str(payload.get("industry", "")),
    )
    x_row = vectorizer.transform([feat])
    pred = float(model.predict(x_row)[0])

    residual_std = float(metrics.get("residual_std", max(1.0, pred * 0.15)))
    band = 1.28 * residual_std
    salary_min = round(max(0.1, pred - band), 1)
    salary_max = round(max(salary_min + 0.1, pred + band), 1)

    rmse = float(metrics.get("rmse", residual_std))
    confidence = max(0.5, min(0.97, 1.0 - rmse / max(pred, 1.0) * 0.35))

    shap_explanation = _compute_shap_explanation(artifact, x_row, top_n=8)

    return {
        "predicted_salary_min": salary_min,
        "predicted_salary_max": salary_max,
        "unit": "K/月",
        "confidence": round(confidence, 2),
        "shap_explanation": shap_explanation,
        "model_info": {
            "model_type": artifact.get("model_type", "xgboost"),
            "trained_at": artifact.get("trained_at"),
            "sample_count": metrics.get("sample_count", 0),
            "rmse": metrics.get("rmse"),
        },
    }
