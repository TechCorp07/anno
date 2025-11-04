"""
Views for MRI Training Platform Assessment
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from assessment.utils import create_test_attempts_bulk
from django.contrib.auth.models import User
from .forms import CandidateRegistrationForm, UserProfileUpdateForm

from .models import Test, TestAttempt, Question, Answer


def home(request):
    """Home page"""
    return render(request, 'assessment/home.html')


def register(request):
    """Enhanced candidate registration with comprehensive data collection"""
    if request.method == 'POST':
        form = CandidateRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, 
                f'Welcome {user.get_full_name()}! Your account has been created successfully.'
            )
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CandidateRegistrationForm()
    
    return render(request, 'assessment/register.html', {'form': form})


@login_required
def user_profile(request):
    """
    User profile page where candidates can view and update their information
    Allows existing users to upload CV and update address
    """
    profile = request.user.profile
    
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('user_profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileUpdateForm(instance=profile)
    
    context = {
        'profile': profile,
        'form': form,
    }
    
    return render(request, 'assessment/user_profile.html', context)


def login_view(request):
    """User login"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'assessment/login.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def dashboard(request):
    """User dashboard showing available tests and past attempts"""
    available_tests = Test.objects.filter(is_active=True)
    past_attempts = TestAttempt.objects.filter(user=request.user)[:10]
    
    context = {
        'available_tests': available_tests,
        'past_attempts': past_attempts,
    }
    return render(request, 'assessment/dashboard.html', context)


@login_required
def test_detail(request, test_id):
    """Display test information before starting"""
    test = get_object_or_404(Test, id=test_id, is_active=True)
    
    # Get user's previous attempts
    previous_attempts = TestAttempt.objects.filter(
        user=request.user,
        test=test
    ).order_by('-started_at')[:5]
    
    context = {
        'test': test,
        'previous_attempts': previous_attempts,
    }
    return render(request, 'assessment/test_detail.html', context)


@login_required
def start_test(request, test_id):
    """Start a new test attempt"""
    test = get_object_or_404(Test, id=test_id, is_active=True)
    
    # Check if user has an active attempt
    active_attempt = TestAttempt.objects.filter(
        user=request.user,
        test=test,
        status__in=['started', 'in_progress']
    ).first()
    
    if active_attempt:
        # Check if expired
        if active_attempt.is_expired():
            active_attempt.status = 'expired'
            active_attempt.save()
        else:
            # Continue existing attempt
            return redirect('take_test', attempt_id=active_attempt.id)
    
    # Create new attempt
    attempt = TestAttempt.objects.create(
        user=request.user,
        test=test,
        status='in_progress'
    )
    
    messages.success(request, f'Test started! You have {test.time_limit_minutes} minutes.')
    return redirect('take_test', attempt_id=attempt.id)

@login_required
def take_test(request, attempt_id):
    """
    Handle test taking with proctoring - Compatible with Alpine.js template
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Check if test has expired
    if attempt.is_expired():
        attempt.status = 'expired'
        attempt.save()
        messages.error(request, 'This test has expired.')
        return redirect('dashboard')
    
    # Generate question set if not already done
    if not attempt.question_set:
        questions = attempt.test.generate_question_set()
        attempt.question_set = [q.id for q in questions]
        attempt.status = 'in_progress'
        attempt.save()
    
    # Get ALL questions from stored question_set (for Alpine.js template)
    from assessment.models import Question
    question_ids = attempt.question_set
    questions = Question.objects.filter(id__in=question_ids)
    
    # Preserve order from question_set
    questions = sorted(questions, key=lambda q: question_ids.index(q.id))
    
    context = {
        'attempt': attempt,
        'questions': questions,  # All questions for Alpine.js
        'time_remaining': attempt.time_remaining_seconds(),
    }
    
    return render(request, 'assessment/take_test.html', context)

@login_required
@require_http_methods(["POST"])
def submit_answer(request, attempt_id):
    """Submit answer for a question (HTMX endpoint)"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Check if expired
    if attempt.is_expired() or attempt.status == 'completed':
        return JsonResponse({
            'success': False,
            'error': 'Test is no longer active'
        }, status=400)
    
    question_id = request.POST.get('question_id')
    selected_answer = request.POST.get('answer')
    
    clicked_x = request.POST.get('clicked_x')
    clicked_y = request.POST.get('clicked_y')
    
    question = get_object_or_404(Question, id=question_id)
    
    if question.question_type == 'dicom' and clicked_x and clicked_y:
        answer, created = Answer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={'clicked_coordinates': {'x': int(clicked_x), 'y': int(clicked_y)}}
        )
        answer.check_answer()
        return JsonResponse({
            'success': True,
            'is_correct': answer.is_correct,
            'question_id': question.id
        })
        
    # Create or update answer
    answer, created = Answer.objects.update_or_create(
        attempt=attempt,
        question=question,
        defaults={
            'selected_answer': selected_answer
        }
    )
    
    # Check if answer is correct
    answer.check_answer()
    
    return JsonResponse({
        'success': True,
        'is_correct': answer.is_correct,
        'question_id': question.id
    })


@login_required
def get_time_remaining(request, attempt_id):
    """Get remaining time for test (HTMX endpoint)"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    time_remaining = attempt.time_remaining_seconds()
    
    return JsonResponse({
        'time_remaining': time_remaining,
        'is_expired': attempt.is_expired()
    })


@login_required
@require_http_methods(["POST", "GET"])
def submit_test(request, attempt_id):
    """
    UPDATED: Submit the entire test with support for disqualification
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    if attempt.status == 'completed':
        messages.info(request, 'This test has already been submitted.')
        return redirect('test_result', attempt_id=attempt.id)
    
    if request.method == 'POST':
        is_disqualified = request.POST.get('disqualified') == 'true'
        disqualification_reason = request.POST.get('disqualification_reason', '')
    else:  # GET request (fallback)
        is_disqualified = request.GET.get('disqualified') == 'true'
        reason_param = request.GET.get('reason', '')
        disqualification_reason = reason_param.replace('_', ' ').title()
        if not disqualification_reason:
            disqualification_reason = 'Fullscreen exit violation'
        
    # Calculate time spent
    time_spent = (timezone.now() - attempt.started_at).total_seconds()
    attempt.time_spent_seconds = int(time_spent)
    
    # Mark as completed
    attempt.status = 'completed'
    attempt.completed_at = timezone.now()
    
    # NEW: Handle disqualification
    if is_disqualified:
        # Mark all answers as incorrect (0% score)
        question_ids = attempt.question_set or []
        for question_id in question_ids:
            question = Question.objects.get(id=question_id)
            # Create Answer object marking as incorrect
            Answer.objects.update_or_create(
                attempt=attempt,
                question=question,
                defaults={'is_correct': False}  # All answers marked incorrect
            )
        
        # Force score to 0%
        attempt.score = 0.0
        attempt.passed = False
        
        # Store disqualification metadata
        if not attempt.metadata:
            attempt.metadata = {}
        attempt.metadata['disqualified'] = True
        attempt.metadata['disqualification_reason'] = disqualification_reason
        attempt.metadata['disqualification_timestamp'] = timezone.now().isoformat()
        
        attempt.save()
        
        messages.error(request, 
            f'⚠️ EXAM DISQUALIFIED: {disqualification_reason}. Your score has been set to 0%.')
        
    else:
        # Normal submission - process answers normally
        question_ids = attempt.question_set or []
        for question_id in question_ids:
            question = Question.objects.get(id=question_id)
            # Create Answer object if it doesn't exist (for unanswered questions)
            answer, created = Answer.objects.get_or_create(
                attempt=attempt,
                question=question,
                defaults={'is_correct': False}  # Unanswered = incorrect
            )
            # Check answer for all (in case some weren't checked when submitted)
            if answer.is_correct is None:
                answer.check_answer()
        
        # Calculate score normally
        attempt.calculate_score()
        
        messages.success(request, 'Test submitted successfully!')
    
    return redirect('test_result', attempt_id=attempt.id)


@login_required
def test_result(request, attempt_id):
    """Display test results"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Get all answers with questions
    answers = attempt.answers.select_related('question').all()
    
    context = {
        'attempt': attempt,
        'answers': answers,
        'total_questions': attempt.test.get_total_questions(),
        'correct_answers': answers.filter(is_correct=True).count(),
    }
    return render(request, 'assessment/test_result.html', context)

@login_required
def dicom_question_view(request, attempt_id, question_id):
    """
    Display DICOM question with Cornerstone3D viewer
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    question = get_object_or_404(Question, id=question_id, question_type='dicom')
    
    # Check if test is still active
    if attempt.is_expired() or attempt.status == 'completed':
        return redirect('test_result', attempt_id=attempt.id)
    
    # Check if this question is already answered
    try:
        answer = Answer.objects.get(attempt=attempt, question=question)
        already_answered = True
    except Answer.DoesNotExist:
        already_answered = False
    
    context = {
        'attempt': attempt,
        'question': question,
        'already_answered': already_answered,
        'show_feedback': False,  # Set to True for training mode
        'show_explanation': False,  # Set to True for training mode
    }
    
    return render(request, 'assessment/dicom_question.html', context)


@login_required
@require_http_methods(["POST"])
def submit_dicom_answer(request, attempt_id):
    """
    Submit DICOM answer with clicked coordinates
    Enhanced version of submit_answer for DICOM questions
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Check if expired
    if attempt.is_expired() or attempt.status == 'completed':
        return JsonResponse({
            'success': False,
            'error': 'Test is no longer active'
        }, status=400)
    
    question_id = request.POST.get('question_id')
    
    # Check for DICOM coordinates
    clicked_x = request.POST.get('clicked_x')
    clicked_y = request.POST.get('clicked_y')
    
    # Check for MCQ answer
    selected_answer = request.POST.get('answer')
    
    if not question_id:
        return JsonResponse({
            'success': False,
            'error': 'Missing question_id'
        }, status=400)
    
    question = get_object_or_404(Question, id=question_id)
    
    # Handle DICOM question with coordinates
    if question.question_type == 'dicom' and clicked_x and clicked_y:
        answer, created = Answer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={
                'clicked_coordinates': {
                    'x': int(clicked_x),
                    'y': int(clicked_y)
                }
            }
        )
        
        # Check if answer is correct (within hotspot)
        is_correct = answer.check_answer()
        
        return JsonResponse({
            'success': True,
            'is_correct': is_correct,
            'question_id': question.id,
            'question_type': 'dicom'
        })
    
    # Handle regular MCQ answer
    elif selected_answer:
        answer, created = Answer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={
                'selected_answer': selected_answer
            }
        )
        
        # Check if answer is correct
        is_correct = answer.check_answer()
        
        return JsonResponse({
            'success': True,
            'is_correct': is_correct,
            'question_id': question.id,
            'question_type': question.question_type
        })
    
    else:
        return JsonResponse({
            'success': False,
            'error': 'Invalid answer format'
        }, status=400)

def terms_conditions(request):
    return render(request, 'assessment/terms_conditions.html')

def privacy_policy(request):
    return render(request, 'assessment/privacy_policy.html')

#users = User.objects.filter(cohort_memberships__cohort=my_cohort)
#attempts = create_test_attempts_bulk(test, users)