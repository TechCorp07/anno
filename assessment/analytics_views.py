"""
Analytics Dashboard Views
Features: Percentile rankings, skill gap analysis, TAO rubric scoring
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count, Q, F
from assessment.models import TestAttempt, Answer, TestCategory, ProctoringEvent, Test
from collections import defaultdict
import numpy as np


@login_required
def user_analytics_dashboard(request):
    """
    User-facing analytics dashboard
    Shows: pass/fail, percentile ranking, skill gaps
    """
    user = request.user
    attempts = TestAttempt.objects.filter(
        user=user,
        status='completed'
    ).select_related('test__category').order_by('-completed_at')
    
    avg_score_decimal = attempts.aggregate(Avg('score'))['score__avg']
    context = {
        'attempts': attempts,
        'total_tests': attempts.count(),
        'passed_tests': attempts.filter(passed=True).count(),
        'avg_score': float(avg_score_decimal) if avg_score_decimal is not None else 0
    }
    
    # Calculate percentile ranking for each category
    category_percentiles = {}
    for category in TestCategory.objects.filter(is_active=True):
        percentile = calculate_user_percentile(user, category)
        category_percentiles[category.name] = percentile
    context['category_percentiles'] = category_percentiles
    
    # Skill gap analysis
    skill_gaps = analyze_skill_gaps(user)
    context['skill_gaps'] = skill_gaps
    
    # TAO rubric assessment
    tao_assessment = calculate_tao_rubric_score(user)
    context['tao_assessment'] = tao_assessment
    
    return render(request, 'assessment/analytics_dashboard.html', context)


def calculate_user_percentile(user, category):
    """
    Calculate user's percentile ranking in a specific category
    compared to all other users
    """
    # Get user's average score in this category
    user_attempts = TestAttempt.objects.filter(
        user=user,
        test__category=category,
        status='completed',
        passed__isnull=False
    )
    
    if not user_attempts.exists():
        return None
    
    user_avg_score = user_attempts.aggregate(Avg('score'))['score__avg']
    
    if user_avg_score is None:
        return None
    
    # Get all scores in this category from all users
    all_scores = list(
        TestAttempt.objects.filter(
            test__category=category,
            status='completed',
            passed__isnull=False
        ).exclude(
            user=user
        ).values_list('score', flat=True)
    )
    
    if not all_scores:
        return 100  # Only user who took the test
    
    # Add user's score
    all_scores.append(float(user_avg_score))
    
    # Calculate percentile
    percentile = (sum(1 for score in all_scores if score < user_avg_score) / len(all_scores)) * 100
    
    return round(percentile, 1)


def analyze_skill_gaps(user):
    """
    Analyze user's performance by topic to identify skill gaps
    Returns topics where user scored < 60%
    """
    skill_gaps = []
    
    # Get all user's completed attempts
    attempts = TestAttempt.objects.filter(
        user=user,
        status='completed'
    ).prefetch_related('answers__question__topic')
    
    # Aggregate performance by topic
    topic_performance = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    for attempt in attempts:
        for answer in attempt.answers.all():
            topic = answer.question.topic
            topic_performance[topic]['total'] += 1
            if answer.is_correct:
                topic_performance[topic]['correct'] += 1
    
    # Identify gaps (< 60% accuracy)
    for topic, stats in topic_performance.items():
        if stats['total'] == 0:
            continue
        
        percentage = (stats['correct'] / stats['total']) * 100
        
        if percentage < 60:
            skill_gaps.append({
                'topic': topic.name,
                'category': topic.category.name,
                'percentage': round(percentage, 1),
                'correct': stats['correct'],
                'total': stats['total'],
                'questions_to_improve': max(1, int((0.6 * stats['total']) - stats['correct']))
            })
    
    # Sort by weakest first
    skill_gaps.sort(key=lambda x: x['percentage'])
    
    return skill_gaps


def calculate_tao_rubric_score(user):
    """
    Calculate TAO-style rubric scores for the 4-stage assessment
    Returns readiness for each stage and overall certification readiness
    """
    rubric_scores = {
        'stage_1_cognitive': {'score': 0, 'max': 100, 'passed': False, 'percentile': None},
        'stage_2_detail': {'score': 0, 'max': 100, 'passed': False, 'percentile': None},
        'stage_3_trainability': {'score': 0, 'max': 100, 'passed': False, 'percentile': None},
        'stage_4_domain': {'score': 0, 'max': 100, 'passed': False, 'percentile': None},
        'overall_readiness': 0,
        'certification_ready': False
    }
    
    for stage_num in range(1, 5):
        category = TestCategory.objects.filter(stage_number=stage_num).first()
        if not category:
            continue
        
        # Get user's attempts for this stage
        attempts = TestAttempt.objects.filter(
            user=user,
            test__category=category,
            status='completed'
        )
        
        if attempts.exists():
            avg_score = attempts.aggregate(Avg('score'))['score__avg']
            passed = avg_score >= category.passing_score
            percentile = calculate_user_percentile(user, category)
            
            stage_key = f'stage_{stage_num}_{category.name.lower().split()[0]}'
            if stage_key in rubric_scores:
                rubric_scores[stage_key]['score'] = round(avg_score, 1)
                rubric_scores[stage_key]['passed'] = passed
                rubric_scores[stage_key]['percentile'] = percentile
    
    # Calculate overall readiness (average of all stages)
    stage_scores = [
        v['score'] for k, v in rubric_scores.items() 
        if k.startswith('stage_') and v['score'] > 0
    ]
    
    if stage_scores:
        overall = sum(stage_scores) / len(stage_scores)
        rubric_scores['overall_readiness'] = round(overall, 1)
        
        # Certification ready if all stages passed
        all_passed = all(
            v['passed'] for k, v in rubric_scores.items() 
            if k.startswith('stage_')
        )
        rubric_scores['certification_ready'] = all_passed
    
    return rubric_scores


@user_passes_test(lambda u: u.is_staff)
def admin_analytics_dashboard(request):
    """
    Admin-facing analytics dashboard
    Shows: cohort performance, test statistics, flagged attempts
    """
    # Overall statistics
    total_attempts = TestAttempt.objects.filter(status='completed').count()
    total_users = TestAttempt.objects.values('user').distinct().count()
    pass_rate = TestAttempt.objects.filter(passed=True).count() / total_attempts * 100 if total_attempts > 0 else 0
    
    # Category breakdown
    category_stats = []
    for category in TestCategory.objects.all():
        cat_attempts = TestAttempt.objects.filter(
            test__category=category,
            status='completed'
        )
        
        if cat_attempts.exists():
            avg_score_decimal = cat_attempts.aggregate(Avg('score'))['score__avg']
            category_stats.append({
                'name': category.name,
                'stage': category.stage_number,
                'attempts': cat_attempts.count(),
                'pass_rate': cat_attempts.filter(passed=True).count() / cat_attempts.count() * 100,
                'avg_score': float(avg_score_decimal) if avg_score_decimal is not None else 0
            })
    
    # Flagged attempts
    flagged_attempts = TestAttempt.objects.filter(
        flagged_for_plagiarism=True
    ).select_related('user', 'test')[:20]
    
    # Question difficulty analysis
    from django.db.models import Case, When, Value, IntegerField
    
    question_stats = Answer.objects.values('question__id', 'question__question_text', 'question__difficulty_level').annotate(
        total_answers=Count('id'),
        correct_answers=Count(Case(When(is_correct=True, then=1), output_field=IntegerField())),
    ).annotate(
        success_rate=F('correct_answers') * 100.0 / F('total_answers')
    ).order_by('success_rate')[:20]  # 20 hardest questions
    
    context = {
        'total_attempts': total_attempts,
        'total_users': total_users,
        'pass_rate': round(pass_rate, 1),
        'category_stats': category_stats,
        'flagged_attempts': flagged_attempts,
        'hardest_questions': question_stats,
    }
    
    return render(request, 'admin/admin_analytics.html', context)


def export_analytics_excel(request):
    """
    Export analytics data to Excel for external analysis
    """
    import openpyxl
    from django.http import HttpResponse
    from io import BytesIO
    
    wb = openpyxl.Workbook()
    
    # Sheet 1: All Attempts
    ws1 = wb.active
    ws1.title = "All Attempts"
    ws1.append(['User', 'Test', 'Category', 'Score', 'Passed', 'Time Spent (min)', 'Completed At', 'Flagged'])
    
    attempts = TestAttempt.objects.filter(status='completed').select_related('user', 'test__category')
    for attempt in attempts:
        ws1.append([
            attempt.user.username,
            attempt.test.title,
            attempt.test.category.name,
            float(attempt.score) if attempt.score else 0,
            'Yes' if attempt.passed else 'No',
            round(attempt.time_spent_seconds / 60, 1) if attempt.time_spent_seconds else 0,
            attempt.completed_at.strftime('%Y-%m-%d %H:%M'),
            'Yes' if attempt.flagged_for_plagiarism else 'No'
        ])
    
    # Sheet 2: User Performance Summary
    ws2 = wb.create_sheet("User Summary")
    ws2.append(['Username', 'Total Tests', 'Passed', 'Pass Rate %', 'Avg Score', 'Best Score'])
    
    from django.contrib.auth.models import User
    for user in User.objects.all():
        user_attempts = TestAttempt.objects.filter(user=user, status='completed')
        if user_attempts.exists():
            total = user_attempts.count()
            passed = user_attempts.filter(passed=True).count()
            avg_score = user_attempts.aggregate(Avg('score'))['score__avg']
            best_score = user_attempts.order_by('-score').first().score
            
            ws2.append([
                user.username,
                total,
                passed,
                round(passed / total * 100, 1),
                round(avg_score, 1) if avg_score else 0,
                round(best_score, 1) if best_score else 0
            ])
    
    # Save to response
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=analytics_export.xlsx'
    
    return response

