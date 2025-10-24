"""
Enhanced Admin Configuration for Assessment App
Includes bulk Excel import, cohort management, and analytics
"""
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.utils.html import format_html
from django.http import HttpResponse
import openpyxl
from io import BytesIO
import json
import os

from .models import (
    TestCategory, QuestionTopic, Question, Test, TestAttempt, Answer,
    Cohort, CohortMembership, ProctoringEvent, PlagiarismFlag
)


class QuestionTopicInline(admin.TabularInline):
    model = QuestionTopic
    extra = 1
    fields = ['name', 'description', 'questions_per_test']


@admin.register(TestCategory)
class TestCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'stage_number', 'passing_score', 'is_active', 'question_count']
    list_filter = ['is_active', 'stage_number']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    inlines = [QuestionTopicInline]
    
    def question_count(self, obj):
        count = sum(topic.questions.count() for topic in obj.topics.all())
        return format_html('<b>{}</b>', count)
    question_count.short_description = 'Total Questions'
    
    fieldsets = (
        ('Category Information', {
            'fields': ('name', 'description', 'stage_number')
        }),
        ('Configuration', {
            'fields': ('passing_score', 'is_active')
        }),
    )


@admin.register(QuestionTopic)
class QuestionTopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'questions_per_test', 'question_count', 'created_at']
    list_filter = ['category']
    search_fields = ['name', 'description']
    
    def question_count(self, obj):
        return obj.questions.filter(is_active=True).count()
    question_count.short_description = 'Active Questions'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text_short', 'topic', 'question_type', 'difficulty_level', 
                    'points', 'time_limit_seconds', 'is_active']
    list_filter = ['question_type', 'difficulty_level', 'is_active', 'topic__category']
    search_fields = ['question_text', 'option_a', 'option_b', 'option_c', 'option_d']
    list_editable = ['is_active', 'difficulty_level']
    
    def question_text_short(self, obj):
        text = obj.question_text[:60] + '...' if len(obj.question_text) > 60 else obj.question_text
        
        if obj.question_type in ['dicom', 'image'] and obj.question_image:
            coord_url = reverse('admin:question_set_coordinates', args=[obj.id])
            return format_html(
                '{} <a href="{}" style="margin-left: 10px;" class="button">📍 Set Coordinates</a>',
                text, coord_url
            )
        return text
        
    question_text_short.short_description = 'Question'
    
    fieldsets = (
        ('Question Details', {
            'fields': ('topic', 'question_type', 'question_text', 'question_image', 
                      'difficulty_level', 'time_limit_seconds', 'points')
        }),
        ('Answer Options (MCQ)', {
            'fields': ('option_a', 'option_b', 'option_c', 'option_d', 'correct_answer'),
            'classes': ('collapse',)
        }),
        ('DICOM Question Settings', {
            'fields': ('dicom_file', 'hotspot_coordinates'),
            'classes': ('collapse',)
        }),
        ('Annotation Question Settings', {
            'fields': ('ground_truth_file', 'dice_threshold'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('explanation', 'is_active')
        }),
    )
    
    # Bulk import functionality
    change_list_template = 'admin/question_changelist.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('bulk-import/', self.admin_site.admin_view(self.bulk_import_view), 
                 name='question_bulk_import'),
            path('download-template/', self.admin_site.admin_view(self.download_template_view),
                 name='question_download_template'),
            path('<int:question_id>/set-coordinates/', self.admin_site.admin_view(self.set_coordinates_view), 
             name='question_set_coordinates'),
        ]
        return custom_urls + urls
    
    def set_coordinates_view(self, request, question_id):
        """Interactive coordinate picker for DICOM/image questions"""
        question = self.get_object(request, question_id)
        
        if request.method == 'POST':
            coordinates_json = request.POST.get('hotspot_coordinates', '[]')
            try:
                coordinates = json.loads(coordinates_json)
                question.hotspot_coordinates = coordinates
                question.save()
                messages.success(request, f'Hotspot coordinates saved for question #{question_id}')
                return redirect('admin:assessment_question_change', question_id)
            except json.JSONDecodeError:
                messages.error(request, 'Invalid coordinate data')
        
        # Get image URL
        image_url = question.question_image.url if question.question_image else None
        
        if not image_url:
            messages.error(request, 'No image uploaded for this question')
            return redirect('admin:assessment_question_change', question_id)
        
        # Convert existing coordinates to JSON
        existing_hotspots = json.dumps(question.hotspot_coordinates or [])
        
        context = {
            'question': question,
            'image_url': image_url,
            'existing_hotspots': existing_hotspots,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, question),
        }
        
        return render(request, 'admin/question_coordinate_picker.html', context)

    def bulk_import_view(self, request):
        """Handle bulk Excel import with image folder"""
        if request.method == 'POST':
            excel_file = request.FILES.get('excel_file')
            image_folder = request.FILES.getlist('image_folder')
            
            if not excel_file:
                messages.error(request, 'Please upload an Excel file.')
                return redirect('..')
            
            try:
                # Process images into dictionary
                images_dict = {}
                for img_file in image_folder:
                    # Extract question number from filename (e.g., "Q001.png" -> 1)
                    try:
                        q_num = int(''.join(filter(str.isdigit, img_file.name.split('.')[0])))
                        images_dict[q_num] = img_file
                    except ValueError:
                        continue
                
                # Read Excel file
                wb = openpyxl.load_workbook(excel_file)
                sheet = wb.active
                
                created_count = 0
                error_count = 0
                errors = []
                
                # Skip header row
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=False), start=2):
                    try:
                        # Extract values (adjust column indices as needed)
                        question_number = int(row[0].value) if row[0].value else None
                        topic_name = str(row[1].value) if row[1].value else None
                        question_type = str(row[2].value).lower() if row[2].value else 'mcq'
                        question_text = str(row[3].value) if row[3].value else None
                        option_a = str(row[4].value) if row[4].value else ''
                        option_b = str(row[5].value) if row[5].value else ''
                        option_c = str(row[6].value) if row[6].value else ''
                        option_d = str(row[7].value) if row[7].value else ''
                        correct_answer = str(row[8].value).lower() if row[8].value else None
                        explanation = str(row[9].value) if row[9].value else ''
                        difficulty = int(row[10].value) if row[10].value else 1
                        time_limit = int(row[11].value) if row[11].value else 60
                        points = int(row[12].value) if row[12].value else 1
                        
                        # Validate required fields
                        if not all([question_number, topic_name, question_text]):
                            errors.append(f"Row {row_idx}: Missing required fields")
                            error_count += 1
                            continue
                        
                        # Find or create topic
                        try:
                            topic = QuestionTopic.objects.get(name=topic_name)
                        except QuestionTopic.DoesNotExist:
                            errors.append(f"Row {row_idx}: Topic '{topic_name}' not found")
                            error_count += 1
                            continue
                        
                        # Create question
                        question = Question.objects.create(
                            topic=topic,
                            question_type=question_type,
                            question_text=question_text,
                            option_a=option_a,
                            option_b=option_b,
                            option_c=option_c,
                            option_d=option_d,
                            correct_answer=correct_answer,
                            explanation=explanation,
                            difficulty_level=difficulty,
                            time_limit_seconds=time_limit,
                            points=points,
                            is_active=True
                        )
                        
                        # Attach image if available
                        if question_number in images_dict:
                            question.question_image = images_dict[question_number]
                            question.save()
                        
                        created_count += 1
                        
                    except Exception as e:
                        errors.append(f"Row {row_idx}: {str(e)}")
                        error_count += 1
                        continue
                
                # Show results
                if created_count > 0:
                    messages.success(request, f'Successfully imported {created_count} questions.')
                if error_count > 0:
                    error_msg = f'{error_count} errors occurred:\n' + '\n'.join(errors[:10])
                    if len(errors) > 10:
                        error_msg += f'\n... and {len(errors) - 10} more errors.'
                    messages.warning(request, error_msg)
                
                return redirect('..')
                
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
                return redirect('..')
        
        return render(request, 'admin/bulk_import_form.html')
    
    def download_template_view(self, request):
        """Generate and download Excel template"""
        wb = openpyxl.Workbook()
        sheet = wb.active
        sheet.title = 'Questions Template'
        
        # Headers
        headers = [
            'Question Number', 'Topic Name', 'Question Type', 'Question Text',
            'Option A', 'Option B', 'Option C', 'Option D', 
            'Correct Answer (a/b/c/d)', 'Explanation', 
            'Difficulty (1-5)', 'Time Limit (seconds)', 'Points'
        ]
        sheet.append(headers)
        
        # Sample data
        sheet.append([
            1, 'Verbal Reasoning', 'mcq', 'What is the capital of Zimbabwe?',
            'Harare', 'Bulawayo', 'Mutare', 'Gweru',
            'a', 'Harare is the capital and largest city of Zimbabwe.',
            1, 60, 1
        ])
        
        # Style header
        from openpyxl.styles import Font, PatternFill
        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='CCCCCC', end_color='CCCCCC', fill_type='solid')
        
        # Adjust column widths
        for column in sheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            sheet.column_dimensions[column_letter].width = min(max_length + 2, 50)
        
        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=question_import_template.xlsx'
        
        return response


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'member_count', 'enabled_categories_list', 'is_active']
    list_filter = ['is_active', 'start_date']
    search_fields = ['name', 'description']
    filter_horizontal = ['enabled_categories']
    list_editable = ['is_active']
    
    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'
    
    def enabled_categories_list(self, obj):
        categories = obj.enabled_categories.all()
        return ', '.join([f"Stage {c.stage_number}" for c in categories])
    enabled_categories_list.short_description = 'Enabled Stages'


@admin.register(CohortMembership)
class CohortMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'cohort', 'joined_at']
    list_filter = ['cohort', 'joined_at']
    search_fields = ['user__username', 'cohort__name']
    raw_id_fields = ['user']


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'time_limit_minutes', 'passing_score', 
                    'total_questions', 'attempt_count', 'is_active']
    list_filter = ['is_active', 'category', 'require_webcam', 'require_fullscreen']
    search_fields = ['title', 'description']
    filter_horizontal = ['manual_questions']
    list_editable = ['is_active']
    
    def total_questions(self, obj):
        return obj.get_total_questions()
    total_questions.short_description = 'Questions'
    
    def attempt_count(self, obj):
        return obj.attempts.count()
    attempt_count.short_description = 'Attempts'
    
    fieldsets = (
        ('Test Information', {
            'fields': ('category', 'title', 'description')
        }),
        ('Question Configuration', {
            'fields': ('auto_generate_from_topics', 'manual_questions')
        }),
        ('Test Configuration', {
            'fields': ('time_limit_minutes', 'passing_score', 'is_active')
        }),
        ('Proctoring Settings', {
            'fields': ('require_webcam', 'require_fullscreen', 'snapshot_interval_seconds')
        }),
    )


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ['question', 'selected_answer', 'is_correct', 'time_spent_seconds', 'answered_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'test', 'cohort', 'status', 'score_display', 'passed', 
                    'flagged_for_plagiarism', 'started_at']
    list_filter = ['status', 'passed', 'flagged_for_plagiarism', 'test__category', 'started_at']
    search_fields = ['user__username', 'test__title', 'ip_address']
    readonly_fields = ['user', 'test', 'started_at', 'completed_at', 'time_spent_seconds', 
                       'ip_address', 'user_agent', 'similarity_score']
    inlines = [AnswerInline]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('analytics/', 
                 self.admin_site.admin_view(self.analytics_dashboard_view),
                 name='testattempt_analytics'),
            path('export-analytics/', 
                 self.admin_site.admin_view(self.export_analytics_view),
                 name='testattempt_export'),
        ]
        return custom_urls + urls
    
    def analytics_dashboard_view(self, request):
        """Full analytics dashboard"""
        from assessment.analytics_views import admin_analytics_dashboard
        return admin_analytics_dashboard(request)
    
    def export_analytics_view(self, request):
        """Export analytics to Excel"""
        from assessment.analytics_views import export_analytics_excel
        return export_analytics_excel(request)
    
    def score_display(self, obj):
        if obj.score is not None:
            color = 'green' if obj.passed else 'red'
            return format_html('<b style="color: {};">{:.2f}%</b>', color, obj.score)
        return '-'
    score_display.short_description = 'Score'
    
    fieldsets = (
        ('Attempt Details', {
            'fields': ('user', 'test', 'cohort', 'status')
        }),
        ('Results', {
            'fields': ('score', 'passed')
        }),
        ('Proctoring', {
            'fields': ('ip_address', 'user_agent', 'consent_given', 'consent_timestamp')
        }),
        ('Plagiarism Detection', {
            'fields': ('similarity_score', 'flagged_for_plagiarism')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'time_spent_seconds')
        }),
    )
    
    # Analytics dashboard
    change_list_template = 'admin/test_attempt_changelist.html'
    
    def changelist_view(self, request, extra_context=None):
        """Add analytics to changelist"""
        extra_context = extra_context or {}
        
        # Calculate statistics
        qs = self.get_queryset(request)
        completed = qs.filter(status='completed')
        
        extra_context['total_attempts'] = qs.count()
        extra_context['completed_attempts'] = completed.count()
        extra_context['pass_rate'] = completed.filter(passed=True).count() / completed.count() * 100 if completed.count() > 0 else 0
        extra_context['avg_score'] = completed.aggregate(Avg('score'))['score__avg'] or 0
        extra_context['flagged_count'] = qs.filter(flagged_for_plagiarism=True).count()
        
        # Per-category statistics
        category_stats = []
        for category in TestCategory.objects.all():
            cat_attempts = completed.filter(test__category=category)
            if cat_attempts.exists():
                category_stats.append({
                    'name': category.name,
                    'stage': category.stage_number,
                    'attempts': cat_attempts.count(),
                    'pass_rate': cat_attempts.filter(passed=True).count() / cat_attempts.count() * 100,
                    'avg_score': cat_attempts.aggregate(Avg('score'))['score__avg'],
                })
        extra_context['category_stats'] = category_stats
        
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(ProctoringEvent)
class ProctoringEventAdmin(admin.ModelAdmin):
    list_display = ['attempt_user', 'event_type', 'timestamp', 'has_image']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['attempt__user__username']
    readonly_fields = ['attempt', 'event_type', 'image_file', 'metadata', 'timestamp']
    
    def attempt_user(self, obj):
        return obj.attempt.user.username
    attempt_user.short_description = 'User'
    
    def has_image(self, obj):
        return bool(obj.image_file)
    has_image.boolean = True
    has_image.short_description = 'Image'
    
    def has_add_permission(self, request):
        return False


@admin.register(PlagiarismFlag)
class PlagiarismFlagAdmin(admin.ModelAdmin):
    list_display = ['attempt1_user', 'attempt2_user', 'similarity_percentage', 
                    'reviewed', 'action_taken', 'detected_at']
    list_filter = ['reviewed', 'action_taken', 'detected_at']
    search_fields = ['attempt1__user__username', 'attempt2__user__username']
    readonly_fields = ['attempt1', 'attempt2', 'similarity_percentage', 
                       'matching_answers', 'detected_at']
    
    def attempt1_user(self, obj):
        return obj.attempt1.user.username
    attempt1_user.short_description = 'User 1'
    
    def attempt2_user(self, obj):
        return obj.attempt2.user.username
    attempt2_user.short_description = 'User 2'
    
    fieldsets = (
        ('Plagiarism Detection', {
            'fields': ('attempt1', 'attempt2', 'similarity_percentage', 'matching_answers')
        }),
        ('Review', {
            'fields': ('reviewed', 'reviewer_notes', 'action_taken', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('detected_at',)
        }),
    )

def admin_dashboard_view(request):
    """
    Central admin dashboard - hub for all admin features
    """
    from django.contrib.auth.models import User
    
    # Gather statistics
    total_questions = Question.objects.filter(is_active=True).count()
    total_users = User.objects.count()
    total_attempts = TestAttempt.objects.filter(status='completed').count()
    
    pass_rate = 0
    if total_attempts > 0:
        passed = TestAttempt.objects.filter(passed=True).count()
        pass_rate = (passed / total_attempts) * 100
    
    flagged_count = TestAttempt.objects.filter(flagged_for_plagiarism=True).count()
    
    # Recent activity
    recent_attempts = TestAttempt.objects.select_related('user', 'test').order_by('-started_at')[:50]
    
    context = {
        'total_questions': total_questions,
        'total_users': total_users,
        'total_attempts': total_attempts,
        'pass_rate': pass_rate,
        'flagged_count': flagged_count,
        'recent_attempts': recent_attempts,
    }
    
    return render(request, 'admin/admin_dashboard.html', context)


# Register the custom dashboard URL with Django Admin
_original_get_urls = admin.site.get_urls

def custom_get_urls():
    """Add custom dashboard URL to admin site"""
    from django.urls import path
    
    urls = _original_get_urls()
    custom_urls = [
        path('dashboard/', admin.site.admin_view(admin_dashboard_view), name='admin_dashboard'),
    ]
    return custom_urls + urls

# Override admin site's get_urls method
admin.site.get_urls = custom_get_urls
