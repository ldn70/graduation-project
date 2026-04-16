"""Resume generation APIs."""

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.views import APIView

from core.response import error_response, success_response


class ResumeGenerateView(APIView):
    def post(self, request):
        file_format = (request.data.get("format") or "txt").lower()
        if file_format not in {"txt", "pdf"}:
            return error_response("仅支持 txt/pdf 格式", 400, code="RESUME_FORMAT_UNSUPPORTED")

        user = request.user
        content = "\n".join(
            [
                f"姓名：{user.name or user.username}",
                f"学历：{user.education or '未填写'}",
                f"技能：{user.skills or '未填写'}",
                f"经历：{user.experience or '未填写'}",
            ]
        )

        resume_dir = Path(settings.MEDIA_ROOT) / "resumes"
        resume_dir.mkdir(parents=True, exist_ok=True)

        # MVP: pdf暂时降级为txt内容，扩展时可替换成真实PDF渲染
        suffix = "txt" if file_format == "pdf" else file_format
        filename = f"resume_{user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{suffix}"
        filepath = resume_dir / filename
        filepath.write_text(content, encoding="utf-8")

        return success_response(
            {"file_url": f"/download/{filename}", "format": file_format},
            "简历生成成功",
        )


class ResumeDownloadView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, filename):
        safe_name = Path(filename).name
        filepath = Path(settings.MEDIA_ROOT) / "resumes" / safe_name
        if not filepath.exists() or not filepath.is_file():
            raise Http404("文件不存在")
        return FileResponse(open(filepath, "rb"), as_attachment=True, filename=safe_name)
