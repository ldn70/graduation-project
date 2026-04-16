"""Analysis APIs: recommendation, skills, salary prediction, trends."""

from collections import Counter
import math
import re

from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from core.response import error_response, success_response
from jobs.models import Job, UserAction
from jobs.utils import parse_experience_years, parse_salary_range_k_month, split_skills
from .recommender import RecommenderError, get_hybrid_recommendations
from .salary_model import SalaryModelError, predict_salary_from_payload
from .trend_model import (
    TrendModelError,
    baseline_forecast,
    build_historical_series,
    forecast_from_historical,
)


class RecommendJobsView(APIView):
    def get(self, request):
        try:
            limit = int(request.GET.get("limit", 10))
        except (TypeError, ValueError):
            return error_response("limit 参数格式错误", 400, code="RECOMMEND_LIMIT_INVALID")
        if limit <= 0:
            return error_response("limit 必须大于 0", 400, code="RECOMMEND_LIMIT_INVALID")
        try:
            recommendations = get_hybrid_recommendations(request.user, limit=limit)
            if recommendations:
                return success_response(
                    {"recommendations": recommendations, "total": len(recommendations)},
                    "推荐成功（Hybrid: TF-IDF + CF + LightFM/SVD）",
                )
        except RecommenderError:
            # Model not trained yet -> fallback to legacy online heuristic.
            pass
        except Exception:
            # Any runtime issue in recommender should not break endpoint availability.
            pass

        jobs = list(Job.objects.all()[:500])
        if not jobs:
            return success_response({"recommendations": [], "total": 0}, "暂无职位数据")
        user_skills = split_skills(request.user.skills or "")
        user_action_jobs = set(
            UserAction.objects.filter(user=request.user).values_list("job_id", flat=True)
        )

        similar_user_ids = list(
            UserAction.objects.exclude(user=request.user)
            .filter(job_id__in=user_action_jobs)
            .values_list("user_id", flat=True)
        )
        similar_counter = Counter(similar_user_ids)
        top_similar_users = [uid for uid, _ in similar_counter.most_common(30)]
        cf_job_ids = set(
            UserAction.objects.filter(user_id__in=top_similar_users).values_list("job_id", flat=True)
        )

        recommended = []
        for job in jobs:
            if job.id in user_action_jobs:
                continue
            job_skills = split_skills(job.skills_required or "")
            overlap = len(user_skills & job_skills)
            denom = len(job_skills) if job_skills else 1
            cbf_score = overlap / denom
            cf_boost = 0.5 if job.id in cf_job_ids else 0.0

            final_score = 0.6 * cbf_score + 0.4 * cf_boost
            if final_score < 0.1:
                continue

            recommended.append(
                {
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "match_score": round(final_score, 3),
                    "match_reason": f"技能匹配{int(cbf_score * 100)}% + 行为协同加权",
                }
            )

        if not recommended:
            for job in jobs[:limit]:
                recommended.append(
                    {
                        "job_id": job.id,
                        "title": job.title,
                        "company": job.company,
                        "match_score": 0.1,
                        "match_reason": "新用户冷启动默认推荐",
                    }
                )

        recommended = sorted(recommended, key=lambda x: x["match_score"], reverse=True)
        dedup = []
        seen = set()
        for row in recommended:
            if row["job_id"] in seen:
                continue
            seen.add(row["job_id"])
            dedup.append(row)
            if len(dedup) >= limit:
                break
        return success_response(
            {"recommendations": dedup, "total": len(dedup)},
            "推荐成功（Fallback baseline）",
        )


class SkillDemandView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        industry = request.GET.get("industry", "").strip()
        job_title = request.GET.get("job_title", "").strip()
        try:
            top_n = int(request.GET.get("top_n", 20))
        except (TypeError, ValueError):
            return error_response("top_n 参数格式错误", 400, code="SKILL_DEMAND_TOP_N_INVALID")
        if top_n <= 0:
            return error_response("top_n 必须大于 0", 400, code="SKILL_DEMAND_TOP_N_INVALID")

        query = Q()
        if industry:
            query &= Q(industry__icontains=industry)
        if job_title:
            query &= Q(title__icontains=job_title)

        jobs = Job.objects.filter(query)
        counter = Counter()
        total_jobs = jobs.count()
        for job in jobs:
            counter.update(split_skills(job.skills_required or ""))

        skills = []
        for name, count in counter.most_common(top_n):
            percentage = round((count / total_jobs * 100), 2) if total_jobs else 0.0
            skills.append({"skill_name": name, "count": count, "percentage": percentage})

        return success_response({"skills": skills, "total_jobs": total_jobs}, "分析成功")


class SkillMatchView(APIView):
    def get(self, request):
        job_id = request.GET.get("job_id")
        if not job_id:
            return error_response("缺少 job_id 参数", 400, code="SKILL_MATCH_JOB_ID_REQUIRED")

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return error_response("职位不存在", 404, code="SKILL_MATCH_JOB_NOT_FOUND")

        user_skills = split_skills(request.user.skills or "")
        job_skills = split_skills(job.skills_required or "")
        match = user_skills & job_skills
        missing = job_skills - user_skills
        match_rate = round((len(match) / len(job_skills) * 100), 2) if job_skills else 0.0

        data = {
            "user_skills": sorted(user_skills),
            "job_skills": sorted(job_skills),
            "match_skills": sorted(match),
            "match_rate": match_rate,
            "missing_skills": sorted(missing),
        }
        return success_response(data, "匹配分析成功")


class SalaryPredictView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        payload = {
            "job_title": request.data.get("job_title", ""),
            "education": request.data.get("education", "本科"),
            "experience": request.data.get("experience", ""),
            "skills": request.data.get("skills", []),
            "city": request.data.get("city", ""),
            "industry": request.data.get("industry", ""),
        }
        try:
            result = predict_salary_from_payload(payload)
            return success_response(result, "预测成功（XGBoost + SHAP）")
        except SalaryModelError:
            # Model unavailable: fallback to baseline heuristic.
            pass
        except Exception:
            # Keep endpoint available for demo even if model inference fails.
            pass

        education = str(payload.get("education", "本科"))
        experience = parse_experience_years(payload.get("experience"))
        skills = payload.get("skills", [])
        if isinstance(skills, str):
            skills = [x.strip() for x in re.split(r"[,，/|;\s]+", skills) if x.strip()]
        city = str(payload.get("city", ""))

        edu_factor = {"大专": 0.9, "本科": 1.0, "硕士": 1.15, "博士": 1.3}.get(education, 1.0)
        city_factor = 1.2 if city in {"北京", "上海", "深圳", "广州"} else 1.0
        exp_factor = 1 + min(experience, 10) * 0.06
        skill_factor = 1 + min(len(skills), 12) * 0.03

        salary_samples = []
        for item in Job.objects.exclude(salary__isnull=True).exclude(salary__exact="")[:5000]:
            low, high = parse_salary_range_k_month(item.salary)
            if low is not None and high is not None:
                salary_samples.append((low + high) / 2)

        base = sum(salary_samples) / len(salary_samples) if salary_samples else 10.0
        predicted = base * edu_factor * city_factor * exp_factor * skill_factor
        min_salary = round(predicted * 0.85, 1)
        max_salary = round(predicted * 1.15, 1)

        shap_like = [
            {"feature": "工作经验", "impact": round((exp_factor - 1) * 10, 2)},
            {"feature": "技能数量", "impact": round((skill_factor - 1) * 10, 2)},
            {"feature": "城市系数", "impact": round((city_factor - 1) * 10, 2)},
            {"feature": "学历系数", "impact": round((edu_factor - 1) * 10, 2)},
        ]

        return success_response(
            {
                "predicted_salary_min": min_salary,
                "predicted_salary_max": max_salary,
                "unit": "K/月",
                "confidence": round(max(0.5, min(0.95, 0.7 + math.log1p(len(skills)) * 0.05)), 2),
                "shap_explanation": shap_like,
            },
            "预测成功（Fallback baseline）",
        )


class JobTrendView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        industry = request.GET.get("industry", "").strip()
        job_title = request.GET.get("job_title", "").strip()
        time_range = request.GET.get("time_range", "month").strip().lower()
        include_forecast = request.GET.get("forecast", "false").lower() == "true"

        query = Q()
        if industry:
            query &= Q(industry__icontains=industry)
        if job_title:
            query &= Q(title__icontains=job_title)

        jobs = Job.objects.filter(query).only("publish_time")
        historical = build_historical_series(jobs, time_range=time_range, include_empty=True)

        forecast = []
        model_info = {"backend": "historical_only", "time_range": time_range}
        if include_forecast and historical:
            try:
                result = forecast_from_historical(historical, time_range=time_range, steps=3)
                forecast = result.get("forecast", [])
                model_info = result.get("model_info", model_info)
            except TrendModelError:
                forecast = baseline_forecast(historical, time_range=time_range, steps=3)
                model_info = {"backend": "baseline", "time_range": time_range}
            except Exception:
                forecast = baseline_forecast(historical, time_range=time_range, steps=3)
                model_info = {"backend": "baseline_runtime_fallback", "time_range": time_range}

        return success_response(
            {
                "historical": historical,
                "forecast": forecast,
                "time_range": time_range,
                "model_info": model_info,
            },
            "趋势查询成功",
        )
