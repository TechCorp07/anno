"""
Admin configuration for Assessment app
"""
from django.contrib import admin
from .models import Question, Test, TestAttempt, Answer


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text', 'question_type', 'difficulty_level', 'is_active', 'created_at']
    list_filter = ['question_type', 'difficulty_level', 'is_active']
    search_fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Question Details', {
            'fields': ('question_type', 'question_text', 'question_image', 'difficulty_level')
        }),
        ('Answer Options', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer')
        }),
        ('Additional Info', {
            'fields': ('explanation', 'is_active')
        }),
    )


class QuestionInline(admin.TabularInline):
    model = Test.questions.through
    extra = 1


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'time_limit_minutes', 'passing_score', 'get_total_questions', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    filter_horizontal = ['questions']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Test Information', {
            'fields': ('title', 'description')
        }),
        ('Test Configuration', {
            'fields': ('time_limit_minutes', 'passing_score', 'is_active')
        }),
        ('Questions', {
            'fields': ('questions',)
        }),
    )


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['question', 'selected_answer', 'is_correct', 'answered_at']


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'test', 'status', 'score', 'passed', 'started_at', 'completed_at']
    list_filter = ['status', 'passed', 'started_at']
    search_fields = ['user__username', 'test__title']
    readonly_fields = ['user', 'test', 'started_at', 'completed_at', 'time_spent_seconds']
    inlines = [AnswerInline]
    
    fieldsets = (
        ('Attempt Details', {
            'fields': ('user', 'test', 'status')
        }),
        ('Results', {
            'fields': ('score', 'passed')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'time_spent_seconds')
        }),
    )


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['attempt', 'question', 'selected_answer', 'is_correct', 'answered_at']
    list_filter = ['is_correct', 'answered_at']
    search_fields = ['attempt__user__username', 'question__question_text']
    readonly_fields = ['attempt', 'question', 'answered_at']
