"""
Analytics Dashboard Views
Features: Percentile rankings, skill gap analysis, TAO rubric scoring
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count, Q, F, Max, Min, Sum, StdDev
from assessment.models import TestAttempt, Answer, TestCategory, ProctoringEvent, Test
from django.db.models.functions import TruncDate
from assessment.models import (
    TestAttempt, Answer, TestCategory, ProctoringEvent, 
    Test, Question, QuestionTopic, Cohort, User
)
from django.contrib.auth import get_user_model
from collections import defaultdict
import json
from datetime import timedelta
from django.utils import timezone


User = get_user_model()


MINIMUM_USERS_FOR_PERCENTILE = 5  # Minimum users needed for meaningful percentile comparison

@user_passes_test(lambda u: u.is_staff)
def admin_analytics_dashboard(request):
    """
    Enhanced admin analytics dashboard with comprehensive insights for:
    - Hiring decisions (top performers, certification readiness)
    - Training planning (cohort comparisons, weakness analysis)
    - Testing improvements (question quality, time analysis)
    """
    
    # ===== OVERALL STATISTICS =====
    total_attempts = TestAttempt.objects.filter(status='completed').count()
    total_users = User.objects.filter(test_attempts__isnull=False).distinct().count()
    total_cohorts = Cohort.objects.count()
    
    completed_attempts = TestAttempt.objects.filter(status='completed')
    
    if total_attempts > 0:
        pass_rate = completed_attempts.filter(passed=True).count() / total_attempts * 100
    else:
        pass_rate = 0
    
    avg_score_decimal = completed_attempts.aggregate(Avg('score'))['score__avg']
    avg_score = float(avg_score_decimal) if avg_score_decimal is not None else 0
    
    # ===== HIRING INSIGHTS =====
    
    # 1. TOP PERFORMERS (Certification Ready Candidates)
    certification_ready = []
    all_users_with_attempts = User.objects.filter(
        test_attempts__status='completed'
        ).distinct()
    
    for user in all_users_with_attempts:
        user_attempts = TestAttempt.objects.filter(
            user=user,
            status='completed'
        )
        
        if user_attempts.count() >= 4:  # Completed all 4 stages
            avg_user_score = user_attempts.aggregate(Avg('score'))['score__avg']
            all_passed = user_attempts.filter(passed=False).count() == 0
            
            if all_passed and avg_user_score >= 80:
                # Get cohort info
                cohort_membership = user.cohortmembership_set.first()
                cohort_name = cohort_membership.cohort.name if cohort_membership else "N/A"
                
                certification_ready.append({
                    'user': user,
                    'avg_score': float(avg_user_score),
                    'tests_completed': user_attempts.count(),
                    'cohort': cohort_name,
                    'latest_test': user_attempts.order_by('-completed_at').first().completed_at
                })
    
    # Sort by average score
    certification_ready.sort(key=lambda x: x['avg_score'], reverse=True)
    top_performers = certification_ready[:10]
    
    # 2. STRUGGLING CANDIDATES (Need additional training)
    struggling_candidates = []
    for user in all_users_with_attempts:
        user_attempts = TestAttempt.objects.filter(
            user=user,
            status='completed'
        )
        
        failed_count = user_attempts.filter(passed=False).count()
        total_user_attempts = user_attempts.count()
        
        if total_user_attempts >= 2 and failed_count >= 2:
            avg_user_score = user_attempts.aggregate(Avg('score'))['score__avg']
            cohort_membership = user.cohortmembership_set.first()
            cohort_name = cohort_membership.cohort.name if cohort_membership else "N/A"
            
            struggling_candidates.append({
                'user': user,
                'avg_score': float(avg_user_score) if avg_user_score else 0,
                'failed_count': failed_count,
                'total_attempts': total_user_attempts,
                'cohort': cohort_name
            })
    
    struggling_candidates.sort(key=lambda x: x['avg_score'])
    
    # 3. RED FLAGS (Security & Integrity Issues)
    flagged_users = TestAttempt.objects.filter(
        Q(flagged_for_plagiarism=True) | Q(proctoring_events__severity='high')
    ).select_related('user').distinct()[:20]
    
    red_flags = []
    for attempt in flagged_users:
        proctoring_issues = ProctoringEvent.objects.filter(
            attempt=attempt,
            severity='high'
        ).count()
        
        red_flags.append({
            'user': attempt.user,
            'test': attempt.test.title,
            'plagiarism': attempt.flagged_for_plagiarism,
            'proctoring_issues': proctoring_issues,
            'date': attempt.completed_at
        })
    
    # ===== TRAINING INSIGHTS =====
    
    # 1. COHORT COMPARISON
    cohort_performance = []
    for cohort in Cohort.objects.all():
        cohort_attempts = TestAttempt.objects.filter(
            cohort=cohort,
            status='completed'
        )
        
        if cohort_attempts.exists():
            avg_cohort_score = cohort_attempts.aggregate(Avg('score'))['score__avg']
            pass_rate = cohort_attempts.filter(passed=True).count() / cohort_attempts.count() * 100
            
            cohort_performance.append({
                'name': cohort.name,
                'avg_score': float(avg_cohort_score),
                'pass_rate': round(pass_rate, 1),
                'total_members': cohort.cohortmembership_set.count(),
                'completed_tests': cohort_attempts.count()
            })
    
    cohort_performance.sort(key=lambda x: x['avg_score'], reverse=True)
    
    # 2. TOPIC-LEVEL WEAKNESS ANALYSIS (Where training is needed)
    topic_performance = []
    for topic in QuestionTopic.objects.all():
        topic_answers = Answer.objects.filter(question__topic=topic)
        
        if topic_answers.exists():
            total_answers = topic_answers.count()
            correct_answers = topic_answers.filter(is_correct=True).count()
            success_rate = (correct_answers / total_answers * 100) if total_answers > 0 else 0
            
            topic_performance.append({
                'topic': topic.name,
                'success_rate': round(success_rate, 1),
                'total_questions': topic_answers.count(),
                'needs_training': success_rate < 60
            })
    
    topic_performance.sort(key=lambda x: x['success_rate'])
    weak_topics = [t for t in topic_performance if t['needs_training']][:10]
    
    # 3. STAGE-SPECIFIC PERFORMANCE
    category_stats = []
    for category in TestCategory.objects.all().order_by('stage_number'):
        cat_attempts = TestAttempt.objects.filter(
            test__category=category,
            status='completed'
        )
        
        if cat_attempts.exists():
            avg_score_decimal = cat_attempts.aggregate(Avg('score'))['score__avg']
            pass_rate = cat_attempts.filter(passed=True).count() / cat_attempts.count() * 100
            
            # Average time spent
            avg_time = cat_attempts.aggregate(Avg('time_spent_seconds'))['time_spent_seconds__avg']
            avg_time_minutes = round(avg_time / 60, 1) if avg_time else 0
            
            category_stats.append({
                'name': category.name,
                'stage': category.stage_number,
                'attempts': cat_attempts.count(),
                'pass_rate': round(pass_rate, 1),
                'avg_score': float(avg_score_decimal) if avg_score_decimal is not None else 0,
                'avg_time_minutes': avg_time_minutes,
                'passing_threshold': category.passing_score
            })
    
    # ===== TESTING METHOD IMPROVEMENTS =====
    
    # 1. QUESTION QUALITY ANALYSIS
    question_quality = []
    for question in Question.objects.all()[:100]:  # Sample first 100
        answers = Answer.objects.filter(question=question)
        
        if answers.count() >= 10:  # Only questions with enough data
            total = answers.count()
            correct = answers.filter(is_correct=True).count()
            success_rate = (correct / total * 100) if total > 0 else 0
            
            # Classify question quality
            if success_rate > 90:
                quality = 'too_easy'
            elif success_rate < 30:
                quality = 'too_hard'
            elif 30 <= success_rate <= 40:
                quality = 'needs_review'
            else:
                quality = 'good'
            
            if quality != 'good':
                question_quality.append({
                    'question_id': question.id,
                    'question_text': question.question_text[:100],
                    'difficulty': question.difficulty_level,
                    'success_rate': round(success_rate, 1),
                    'quality': quality,
                    'times_asked': total
                })
    
    # Sort by quality issues
    too_easy = [q for q in question_quality if q['quality'] == 'too_easy']
    too_hard = [q for q in question_quality if q['quality'] == 'too_hard']
    needs_review = [q for q in question_quality if q['quality'] == 'needs_review']
    
    # 2. PROCTORING INSIGHTS
    proctoring_stats = {
        'total_events': ProctoringEvent.objects.count(),
        'high_severity': ProctoringEvent.objects.filter(severity='high').count(),
        'medium_severity': ProctoringEvent.objects.filter(severity='medium').count(),
        'low_severity': ProctoringEvent.objects.filter(severity='low').count(),
    }
    
    # Most common proctoring issues
    event_types = ProctoringEvent.objects.values('event_type').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    proctoring_stats['common_issues'] = [
        {'type': e['event_type'], 'count': e['count']} 
        for e in event_types
    ]
    
    # 3. TEST COMPLETION TIME ANALYSIS
    time_analysis = []
    for test in Test.objects.all():
        test_attempts = TestAttempt.objects.filter(
            test=test,
            status='completed',
            time_spent_seconds__isnull=False
        )
        
        if test_attempts.count() >= 5:
            avg_time = test_attempts.aggregate(Avg('time_spent_seconds'))['time_spent_seconds__avg']
            min_time = test_attempts.aggregate(Min('time_spent_seconds'))['time_spent_seconds__min']
            max_time = test_attempts.aggregate(Max('time_spent_seconds'))['time_spent_seconds__max']
            
            time_analysis.append({
                'test': test.title,
                'avg_minutes': round(avg_time / 60, 1) if avg_time else 0,
                'min_minutes': round(min_time / 60, 1) if min_time else 0,
                'max_minutes': round(max_time / 60, 1) if max_time else 0,
                'time_limit': test.time_limit_minutes,
                'attempts_count': test_attempts.count()
            })
    
    # ===== TREND ANALYSIS (Last 30 days) =====
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_attempts = TestAttempt.objects.filter(
        status='completed',
        completed_at__gte=thirty_days_ago
    )
    
    # Daily completion trend
    daily_completions = recent_attempts.annotate(
        date=TruncDate('completed_at')
    ).values('date').annotate(
        count=Count('id'),
        avg_score=Avg('score')
    ).order_by('date')
    
    trend_data = {
        'dates': [d['date'].strftime('%Y-%m-%d') for d in daily_completions],
        'counts': [d['count'] for d in daily_completions],
        'scores': [float(d['avg_score']) if d['avg_score'] else 0 for d in daily_completions]
    }
    
    # ===== ACTIONABLE RECOMMENDATIONS =====
    recommendations = []
    
    # Check if any cohort is underperforming
    for cohort in cohort_performance:
        if cohort['avg_score'] < 60:
            recommendations.append({
                'priority': 'high',
                'category': 'training',
                'title': f"Cohort '{cohort['name']}' needs additional training",
                'detail': f"Average score of {cohort['avg_score']:.1f}% is below acceptable threshold",
                'action': f"Schedule remedial sessions focusing on weak topics"
            })
    
    # Check if questions need review
    if len(too_easy) > 10:
        recommendations.append({
            'priority': 'medium',
            'category': 'testing',
            'title': f"{len(too_easy)} questions are too easy (>90% success)",
            'detail': "These questions do not effectively differentiate candidates",
            'action': "Review and increase difficulty or replace questions"
        })
    
    if len(too_hard) > 10:
        recommendations.append({
            'priority': 'high',
            'category': 'testing',
            'title': f"{len(too_hard)} questions are too hard (<30% success)",
            'detail': "These questions may be unfair or poorly worded",
            'action': "Review for clarity and accuracy, consider removing"
        })
    
    # Check certification readiness
    if len(certification_ready) < 5:
        recommendations.append({
            'priority': 'high',
            'category': 'hiring',
            'title': "Low number of certification-ready candidates",
            'detail': f"Only {len(certification_ready)} candidates ready for hiring",
            'action': "Increase training quality or adjust passing thresholds"
        })
    
    # Proctoring issues
    if proctoring_stats['high_severity'] > 20:
        recommendations.append({
            'priority': 'high',
            'category': 'security',
            'title': f"{proctoring_stats['high_severity']} high-severity proctoring events",
            'detail': "Multiple candidates flagged for suspicious behavior",
            'action': "Review proctoring footage and investigate flagged attempts"
        })
    
    context = {
        # Overall stats
        'total_attempts': total_attempts,
        'total_users': total_users,
        'total_cohorts': total_cohorts,
        'pass_rate': round(pass_rate, 1),
        'avg_score': round(avg_score, 1),
        
        # Hiring insights
        'top_performers': top_performers,
        'certification_ready_count': len(certification_ready),
        'struggling_candidates': struggling_candidates[:10],
        'red_flags': red_flags,
        
        # Training insights
        'cohort_performance': cohort_performance,
        'weak_topics': weak_topics,
        'category_stats': category_stats,
        
        # Testing improvements
        'too_easy_questions': too_easy[:10],
        'too_hard_questions': too_hard[:10],
        'needs_review_questions': needs_review[:10],
        'proctoring_stats': proctoring_stats,
        'time_analysis': time_analysis,
        
        # Trends
        'trend_data': json.dumps(trend_data),
        
        # Recommendations
        'recommendations': recommendations,
    }
    
    return render(request, 'admin/admin_analytics.html', context)


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
        'avg_score': float(avg_score_decimal) if avg_score_decimal is not None else 0,
        'minimum_users_for_percentile': MINIMUM_USERS_FOR_PERCENTILE
    }
    
    # Calculate percentile ranking for each category
    category_percentiles = {}
    for category in TestCategory.objects.filter(is_active=True):
        percentile_data = calculate_user_percentile(user, category)
        category_percentiles[category.name] = percentile_data
    context['category_percentiles'] = category_percentiles
    
    # Skill gap analysis
    skill_gaps = analyze_skill_gaps(user)
    context['skill_gaps'] = skill_gaps
    
    # TAO rubric assessment
    tao_assessment = calculate_tao_rubric_score(user)
    context['tao_assessment'] = tao_assessment
    
    return render(request, 'assessment/analytics_dashboard.html', context)


def calculate_user_percentile(user, category):
    # Get user's average score in this category
    user_attempts = TestAttempt.objects.filter(
        user=user,
        test__category=category,
        status='completed',
        passed__isnull=False
    )
    
    if not user_attempts.exists():
        return {
            'percentile': None,
            'total_users': 0,
            'user_score': None,
            'has_sufficient_data': False,
            'message': 'No completed tests in this category'
        }
    
    user_avg_score = user_attempts.aggregate(Avg('score'))['score__avg']
    
    if user_avg_score is None:
        return {
            'percentile': None,
            'total_users': 0,
            'user_score': None,
            'has_sufficient_data': False,
            'message': 'Unable to calculate average score'
        }
    
    # Get all scores in this category from all users (excluding current user)
    all_scores = list(
        TestAttempt.objects.filter(
            test__category=category,
            status='completed',
            passed__isnull=False
        ).exclude(
            user=user
        ).values_list('score', flat=True)
    )
    
    total_users = len(all_scores) + 1  # Include current user
    
    # PRODUCTION READY: Check if we have enough users for meaningful comparison
    if len(all_scores) < MINIMUM_USERS_FOR_PERCENTILE - 1:
        return {
            'percentile': None,
            'total_users': total_users,
            'user_score': round(float(user_avg_score), 1),
            'has_sufficient_data': False,
            'message': f'Need at least {MINIMUM_USERS_FOR_PERCENTILE} users for percentile comparison'
        }
    
    # Add user's score to the list for calculation
    all_scores.append(float(user_avg_score))
    
    # Calculate percentile: percentage of scores below the user's score
    scores_below = sum(1 for score in all_scores if score < user_avg_score)
    percentile = (scores_below / len(all_scores)) * 100
    
    return {
        'percentile': round(percentile, 1),
        'total_users': total_users,
        'user_score': round(float(user_avg_score), 1),
        'has_sufficient_data': True,
        'message': None
    }


def analyze_skill_gaps(user):
    """
    Analyze user's performance by topic to identify skill gaps
    Returns topics where user scored < 60%
    
    NO CHANGES - This function works correctly as-is
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
                'avg_score': round(percentage, 1),
                'correct': stats['correct'],
                'total': stats['total'],
                'attempt_count': stats['total'],
                'questions_needed': max(1, int((0.6 * stats['total']) - stats['correct']))
            })
    
    # Sort by weakest first
    skill_gaps.sort(key=lambda x: x['avg_score'])
    
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
            
            # UPDATED: Use new percentile calculation
            percentile_data = calculate_user_percentile(user, category)
            percentile_value = percentile_data['percentile'] if percentile_data['has_sufficient_data'] else None
            
            stage_key = f'stage_{stage_num}_{category.name.lower().split()[0]}'
            if stage_key in rubric_scores:
                rubric_scores[stage_key]['score'] = round(avg_score, 1)
                rubric_scores[stage_key]['passed'] = passed
                rubric_scores[stage_key]['percentile'] = percentile_value
    
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

