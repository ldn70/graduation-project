"""Hybrid recommendation training/inference helpers.

This module provides:
1) Offline training artifact building (TF-IDF + CF + LightFM/SVD fallback)
2) Artifact persistence and cached loading
3) Online recommendation scoring for a user
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os
import pickle
from typing import Any

from django.conf import settings
from django.utils import timezone

from jobs.models import UserAction
from jobs.utils import split_skills


ACTION_WEIGHTS = {
    "view": 1.0,
    "click": 1.2,
    "favorite": 2.5,
}

_MODEL_CACHE: dict[str, Any] = {}


@dataclass
class SimpleJob:
    id: int
    title: str
    company: str
    industry: str
    location: str
    education: str
    experience: str
    skills_required: str
    description: str


@dataclass
class SimpleAction:
    user_id: int
    job_id: int
    action_type: str


class RecommenderError(Exception):
    """Raised when recommendation model training/loading fails."""


def _require_sklearn():
    try:
        from scipy.sparse import csr_matrix  # noqa: F401
        from sklearn.decomposition import TruncatedSVD  # noqa: F401
        from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
        from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401
    except Exception as exc:
        raise RecommenderError(
            "scikit-learn/scipy is required. Install backend dependencies first."
        ) from exc


def _require_numpy():
    try:
        import numpy as np
    except Exception as exc:
        raise RecommenderError("numpy is required. Install backend dependencies first.") from exc
    return np


def default_model_path() -> Path:
    configured = os.getenv("RECOMMENDER_MODEL_PATH")
    if configured:
        return Path(configured).expanduser().resolve()
    return (settings.BASE_DIR / "analysis" / "models" / "hybrid_recommender.pkl").resolve()


def save_artifact(artifact: dict[str, Any], output_path: Path | str | None = None) -> Path:
    path = Path(output_path) if output_path else default_model_path()
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(artifact, f)
    return path


def load_artifact(model_path: Path | str | None = None, use_cache: bool = True) -> dict[str, Any] | None:
    path = Path(model_path) if model_path else default_model_path()
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


def _build_job_text(job: SimpleJob) -> str:
    parts = [
        job.title or "",
        job.company or "",
        job.industry or "",
        job.location or "",
        job.education or "",
        job.experience or "",
        job.skills_required or "",
        job.description or "",
    ]
    return " ".join(p.strip() for p in parts if p and p.strip())


def _normalize(arr):
    np = _require_numpy()
    if arr.size == 0:
        return arr
    lo = float(np.min(arr))
    hi = float(np.max(arr))
    if abs(hi - lo) < 1e-12:
        return np.zeros_like(arr, dtype=float)
    return (arr - lo) / (hi - lo)


def _user_query_text(user) -> str:
    skill_tokens = sorted(split_skills(user.skills or ""))
    return " ".join(
        token
        for token in [
            " ".join(skill_tokens),
            user.education or "",
            user.experience or "",
            user.name or "",
        ]
        if token
    )


def train_hybrid_artifact(
    jobs: list[SimpleJob],
    actions: list[SimpleAction],
    alpha_cbf: float = 0.5,
    alpha_cf: float = 0.3,
    alpha_lfm: float = 0.2,
) -> dict[str, Any]:
    np = _require_numpy()
    _require_sklearn()
    from scipy.sparse import csr_matrix
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    if not jobs:
        raise RecommenderError("No jobs found for training.")

    alpha_sum = alpha_cbf + alpha_cf + alpha_lfm
    if alpha_sum <= 0:
        raise RecommenderError("Invalid alpha weights: all zeros.")
    alpha_cbf /= alpha_sum
    alpha_cf /= alpha_sum
    alpha_lfm /= alpha_sum

    job_ids = [job.id for job in jobs]
    job_id_to_index = {job_id: idx for idx, job_id in enumerate(job_ids)}
    texts = [_build_job_text(job) for job in jobs]

    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), min_df=1)
    job_tfidf = vectorizer.fit_transform(texts)

    user_ids = sorted({a.user_id for a in actions})
    user_id_to_index = {uid: idx for idx, uid in enumerate(user_ids)}

    if user_ids:
        rows: list[int] = []
        cols: list[int] = []
        data: list[float] = []
        for action in actions:
            user_idx = user_id_to_index.get(action.user_id)
            item_idx = job_id_to_index.get(action.job_id)
            if user_idx is None or item_idx is None:
                continue
            rows.append(user_idx)
            cols.append(item_idx)
            data.append(float(ACTION_WEIGHTS.get(action.action_type, 1.0)))
        user_item = csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(job_ids)))
    else:
        user_item = csr_matrix((0, len(job_ids)))

    if user_item.shape[0] > 0:
        popularity = np.asarray(user_item.sum(axis=0)).ravel().astype(float)
    else:
        popularity = np.zeros(len(job_ids), dtype=float)

    lfm_backend = "svd"
    lfm_model = None
    user_factors = None
    item_factors = None

    if user_item.shape[0] >= 2 and user_item.shape[1] >= 2 and user_item.nnz > 0:
        try:
            from lightfm import LightFM

            model = LightFM(no_components=16, loss="warp", random_state=42)
            model.fit(user_item, epochs=25, num_threads=1)
            lfm_backend = "lightfm"
            lfm_model = model
        except Exception:
            n_components = int(min(16, user_item.shape[0] - 1, user_item.shape[1] - 1))
            if n_components >= 1:
                svd = TruncatedSVD(n_components=n_components, random_state=42)
                user_factors = svd.fit_transform(user_item)
                item_factors = svd.components_.T

    job_meta = {
        job.id: {
            "title": job.title,
            "company": job.company,
        }
        for job in jobs
    }

    return {
        "model_version": 1,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "alpha": {"cbf": alpha_cbf, "cf": alpha_cf, "lfm": alpha_lfm},
        "job_ids": job_ids,
        "job_id_to_index": job_id_to_index,
        "job_meta": job_meta,
        "tfidf_vectorizer": vectorizer,
        "job_tfidf": job_tfidf,
        "user_ids": user_ids,
        "user_id_to_index": user_id_to_index,
        "user_item": user_item,
        "popularity": popularity,
        "lfm_backend": lfm_backend,
        "lfm_model": lfm_model,
        "user_factors": user_factors,
        "item_factors": item_factors,
    }


def _score_cbf(artifact: dict[str, Any], user_id: int | None, query_text: str):
    np = _require_numpy()
    from sklearn.metrics.pairwise import cosine_similarity

    job_tfidf = artifact["job_tfidf"]
    vectorizer = artifact["tfidf_vectorizer"]
    user_item = artifact["user_item"]
    user_id_to_index = artifact["user_id_to_index"]

    vectors = []
    if query_text.strip():
        vectors.append(vectorizer.transform([query_text]))

    if user_id is not None and user_id in user_id_to_index and user_item.shape[0] > 0:
        user_idx = user_id_to_index[user_id]
        profile = user_item[user_idx].dot(job_tfidf)
        if getattr(profile, "nnz", 0) > 0:
            vectors.append(profile)

    if not vectors:
        return np.zeros(job_tfidf.shape[0], dtype=float)

    combined = vectors[0]
    for vec in vectors[1:]:
        combined = combined + vec
    scores = cosine_similarity(combined, job_tfidf).ravel()
    return np.asarray(scores, dtype=float)


def _score_cf(artifact: dict[str, Any], user_id: int | None):
    np = _require_numpy()
    from sklearn.metrics.pairwise import cosine_similarity

    user_item = artifact["user_item"]
    user_id_to_index = artifact["user_id_to_index"]
    n_items = len(artifact["job_ids"])

    if user_id is None or user_id not in user_id_to_index or user_item.shape[0] == 0:
        return np.zeros(n_items, dtype=float)

    user_idx = user_id_to_index[user_id]
    sim = cosine_similarity(user_item[user_idx], user_item).ravel()
    sim[user_idx] = 0.0

    denom = float(np.abs(sim).sum())
    if denom < 1e-12:
        return np.zeros(n_items, dtype=float)

    scores = user_item.T.dot(sim) / denom
    return np.asarray(scores, dtype=float).ravel()


def _score_lfm(artifact: dict[str, Any], user_id: int | None):
    np = _require_numpy()
    n_items = len(artifact["job_ids"])
    user_id_to_index = artifact["user_id_to_index"]

    if user_id is None or user_id not in user_id_to_index:
        return np.asarray(artifact["popularity"], dtype=float)

    user_idx = user_id_to_index[user_id]
    backend = artifact.get("lfm_backend", "svd")
    if backend == "lightfm" and artifact.get("lfm_model") is not None:
        model = artifact["lfm_model"]
        scores = model.predict(user_idx, np.arange(n_items))
        return np.asarray(scores, dtype=float)

    user_factors = artifact.get("user_factors")
    item_factors = artifact.get("item_factors")
    if user_factors is not None and item_factors is not None:
        return np.asarray(user_factors[user_idx].dot(item_factors.T), dtype=float)

    return np.asarray(artifact["popularity"], dtype=float)


def get_hybrid_recommendations(user, limit: int = 10, model_path: Path | str | None = None) -> list[dict[str, Any]]:
    np = _require_numpy()
    artifact = load_artifact(model_path=model_path, use_cache=True)
    if artifact is None:
        raise RecommenderError("Hybrid recommender model is not trained yet.")

    limit = max(1, min(int(limit or 10), 50))
    query_text = _user_query_text(user)

    cbf_raw = _score_cbf(artifact, user.id, query_text)
    cf_raw = _score_cf(artifact, user.id)
    lfm_raw = _score_lfm(artifact, user.id)

    cbf = _normalize(cbf_raw)
    cf = _normalize(cf_raw)
    lfm = _normalize(lfm_raw)

    alpha = artifact.get("alpha", {"cbf": 0.5, "cf": 0.3, "lfm": 0.2})
    final = alpha["cbf"] * cbf + alpha["cf"] * cf + alpha["lfm"] * lfm

    seen_job_ids = set(UserAction.objects.filter(user=user).values_list("job_id", flat=True))

    ranking = np.argsort(-final)
    job_ids = artifact["job_ids"]
    job_meta = artifact["job_meta"]

    output: list[dict[str, Any]] = []
    for idx in ranking:
        job_id = job_ids[int(idx)]
        if job_id in seen_job_ids:
            continue
        score = float(final[int(idx)])
        if score <= 0 and len(output) >= max(3, limit // 2):
            continue

        signal_parts = sorted(
            [
                ("TF-IDF", float(cbf[int(idx)])),
                ("CF", float(cf[int(idx)])),
                ("LightFM", float(lfm[int(idx)])),
            ],
            key=lambda x: x[1],
            reverse=True,
        )
        reason = f"{signal_parts[0][0]}主导 + {signal_parts[1][0]}补充"
        meta = job_meta[job_id]
        output.append(
            {
                "job_id": job_id,
                "title": meta["title"],
                "company": meta["company"],
                "match_score": round(score, 3),
                "match_reason": reason,
            }
        )
        if len(output) >= limit:
            break

    if output:
        return output

    popularity = np.asarray(artifact["popularity"], dtype=float)
    pop_rank = np.argsort(-popularity)
    for idx in pop_rank:
        job_id = job_ids[int(idx)]
        if job_id in seen_job_ids:
            continue
        meta = job_meta[job_id]
        output.append(
            {
                "job_id": job_id,
                "title": meta["title"],
                "company": meta["company"],
                "match_score": 0.1,
                "match_reason": "冷启动热门职位推荐",
            }
        )
        if len(output) >= limit:
            break
    return output


def build_training_data_from_db(max_jobs: int = 10000) -> tuple[list[SimpleJob], list[SimpleAction]]:
    from jobs.models import Job

    max_jobs = max(1, int(max_jobs))
    job_rows = list(
        Job.objects.order_by("-publish_time", "-id")[:max_jobs].values(
            "id",
            "title",
            "company",
            "industry",
            "location",
            "education",
            "experience",
            "skills_required",
            "description",
        )
    )
    jobs = [
        SimpleJob(
            id=row["id"],
            title=row["title"] or "",
            company=row["company"] or "",
            industry=row["industry"] or "",
            location=row["location"] or "",
            education=row["education"] or "",
            experience=row["experience"] or "",
            skills_required=row["skills_required"] or "",
            description=row["description"] or "",
        )
        for row in job_rows
    ]

    if not jobs:
        return [], []

    job_ids = [j.id for j in jobs]
    action_rows = list(
        UserAction.objects.filter(job_id__in=job_ids).values("user_id", "job_id", "action_type")
    )
    actions = [
        SimpleAction(
            user_id=row["user_id"],
            job_id=row["job_id"],
            action_type=row["action_type"] or "view",
        )
        for row in action_rows
    ]
    return jobs, actions


def retrain_and_save(
    output_path: Path | str | None = None,
    max_jobs: int = 10000,
    alpha_cbf: float = 0.5,
    alpha_cf: float = 0.3,
    alpha_lfm: float = 0.2,
) -> dict[str, Any]:
    jobs, actions = build_training_data_from_db(max_jobs=max_jobs)
    artifact = train_hybrid_artifact(
        jobs=jobs,
        actions=actions,
        alpha_cbf=alpha_cbf,
        alpha_cf=alpha_cf,
        alpha_lfm=alpha_lfm,
    )
    output = save_artifact(artifact, output_path=output_path)
    artifact["saved_to"] = str(output)
    artifact["trained_at_tz"] = timezone.now().isoformat(timespec="seconds")
    return artifact
