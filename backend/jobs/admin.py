from django.contrib import admin

from .models import Favorite, Job, Recommendation, UserAction


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "company", "education", "location", "publish_time")
    search_fields = ("title", "company", "skills_required")


admin.site.register(UserAction)
admin.site.register(Favorite)
admin.site.register(Recommendation)
