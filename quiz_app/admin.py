from django.contrib import admin

from .models import Question, Quiz


class QuestionInline(admin.StackedInline):
    """Display and edit questions directly inside the quiz admin page."""

    model = Question
    extra = 0
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Admin configuration for quizzes including their questions."""

    list_display = ["title", "user", "created_at", "updated_at"]
    list_filter = ["created_at"]
    search_fields = ["title", "description", "user__username"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """Admin configuration for editing single questions."""

    list_display = ["question_title", "quiz", "answer"]
    list_filter = ["quiz"]
    search_fields = ["question_title", "quiz__title"]
    readonly_fields = ["created_at", "updated_at"]
