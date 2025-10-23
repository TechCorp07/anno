"""
Views for MRI Training Platform Assessment
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Test, TestAttempt, Question, Answer


def home(request):
    """Home page"""
    return render(request, 'assessment/home.html')


def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to MRI Training Platform.')
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'assessment/register.html', {'form': form})


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
    """Take the test - display questions"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Check if already completed
    if attempt.status == 'completed':
        messages.info(request, 'This test has already been completed.')
        return redirect('test_result', attempt_id=attempt.id)
    
    # Check if expired
    if attempt.is_expired():
        attempt.status = 'expired'
        attempt.save()
        messages.error(request, 'Test time has expired.')
        return redirect('test_result', attempt_id=attempt.id)
    
    # Get all questions for this test
    questions = attempt.test.questions.all()
    
    # Get already answered questions
    answered_question_ids = attempt.answers.values_list('question_id', flat=True)
    
    context = {
        'attempt': attempt,
        'questions': questions,
        'answered_question_ids': list(answered_question_ids),
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
    
    question = get_object_or_404(Question, id=question_id)
    
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
@require_http_methods(["POST"])
def submit_test(request, attempt_id):
    """Submit the entire test"""
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    if attempt.status == 'completed':
        messages.info(request, 'This test has already been submitted.')
        return redirect('test_result', attempt_id=attempt.id)
    
    # Calculate time spent
    time_spent = (timezone.now() - attempt.started_at).total_seconds()
    attempt.time_spent_seconds = int(time_spent)
    
    # Mark as completed
    attempt.status = 'completed'
    attempt.completed_at = timezone.now()
    
    # Calculate score
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
