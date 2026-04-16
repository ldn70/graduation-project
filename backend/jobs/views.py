"""API views for jobs."""

from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from core.response import error_response, success_response
from .models import Job
from .serializers import JobListSerializer
from .utils import parse_salary_range_k_month


class JobSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = Q()
        keyword = request.GET.get("keyword", "").strip()
        education = request.GET.get("education", "").strip()
        salary_min = request.GET.get("salary_min")
        salary_max = request.GET.get("salary_max")
        try:
            page = int(request.GET.get("page", 1))
        except (TypeError, ValueError):
            return error_response("page 参数格式错误", 400, code="JOB_SEARCH_PAGE_INVALID")
        try:
            per_page = int(request.GET.get("per_page", 10))
        except (TypeError, ValueError):
            return error_response("per_page 参数格式错误", 400, code="JOB_SEARCH_PER_PAGE_INVALID")
        if page <= 0:
            return error_response("page 必须大于 0", 400, code="JOB_SEARCH_PAGE_INVALID")
        if per_page <= 0:
            return error_response("per_page 必须大于 0", 400, code="JOB_SEARCH_PER_PAGE_INVALID")

        if keyword:
            query &= (
                Q(title__icontains=keyword)
                | Q(company__icontains=keyword)
                | Q(skills_required__icontains=keyword)
            )
        if education:
            query &= Q(education__icontains=education)

        jobs = Job.objects.filter(query)
        jobs = jobs.order_by("-publish_time", "-id")

        try:
            salary_min_num = float(salary_min) if salary_min not in (None, "") else None
        except (TypeError, ValueError):
            salary_min_num = None
        try:
            salary_max_num = float(salary_max) if salary_max not in (None, "") else None
        except (TypeError, ValueError):
            salary_max_num = None

        if salary_min_num is not None or salary_max_num is not None:
            # Limit in-memory filtering to keep the endpoint responsive.
            candidate_ids = []
            for item in jobs[:5000]:
                low, high = parse_salary_range_k_month(item.salary)
                if low is None and high is None:
                    continue
                if salary_min_num is not None and (high is None or high < salary_min_num):
                    continue
                if salary_max_num is not None and (low is None or low > salary_max_num):
                    continue
                candidate_ids.append(item.id)
            jobs = jobs.filter(id__in=candidate_ids).order_by("-publish_time", "-id")

        paginator = Paginator(jobs, per_page)
        page_obj = paginator.get_page(page)
        items = JobListSerializer(page_obj.object_list, many=True).data

        data = {
            "jobs": items,
            "total": paginator.count,
            "pages": paginator.num_pages,
            "current": page_obj.number,
            "per_page": per_page,
        }
        return success_response(data, "查询成功")
