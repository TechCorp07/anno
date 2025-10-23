"""
Proctoring views for handling webcam snapshots and monitoring events
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image
from io import BytesIO
import json

from .models import TestAttempt, ProctoringEvent


@login_required
@require_http_methods(["POST"])
def upload_proctoring_snapshot(request, attempt_id):
    """
    Handle webcam/screen snapshot uploads
    Compress images to ~200KB before saving
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Check if test is still active
    if attempt.status not in ['started', 'in_progress']:
        return JsonResponse({'error': 'Test is not active'}, status=400)
    
    image_file = request.FILES.get('image')
    event_type = request.POST.get('event_type', 'webcam')
    
    if not image_file:
        return JsonResponse({'error': 'No image provided'}, status=400)
    
    try:
        # Open and compress image
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Resize to max 640x480 to ensure ~200KB
        max_size = (640, 480)
        img.thumbnail(max_size, Image.LANCZOS)
        
        # Save to BytesIO with JPEG compression
        output = BytesIO()
        img.save(output, format='JPEG', quality=70, optimize=True)
        output.seek(0)
        
        # Create proctoring event
        event = ProctoringEvent.objects.create(
            attempt=attempt,
            event_type=event_type,
            metadata={
                'original_size': image_file.size,
                'compressed_size': output.tell(),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }
        )
        
        # Save compressed image
        filename = f"{event_type}_{attempt.user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        event.image_file.save(filename, ContentFile(output.read()), save=True)
        
        return JsonResponse({
            'success': True,
            'event_id': event.id,
            'compressed_size': output.tell()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def log_proctoring_event(request, attempt_id):
    """
    Log proctoring events (tab switch, right-click, etc.)
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Check if test is still active
    if attempt.status not in ['started', 'in_progress']:
        return JsonResponse({'error': 'Test is not active'}, status=400)
    
    try:
        data = json.loads(request.body)
        event_type = data.get('event_type')
        metadata = data.get('metadata', {})
        
        # Add request metadata
        metadata.update({
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'remote_addr': request.META.get('REMOTE_ADDR', ''),
            'http_x_forwarded_for': request.META.get('HTTP_X_FORWARDED_FOR', ''),
        })
        
        # Create event
        event = ProctoringEvent.objects.create(
            attempt=attempt,
            event_type=event_type,
            metadata=metadata
        )
        
        # Check for suspicious activity
        if event_type in ['tab_switch', 'fullscreen_exit']:
            recent_violations = ProctoringEvent.objects.filter(
                attempt=attempt,
                event_type__in=['tab_switch', 'fullscreen_exit'],
                timestamp__gte=timezone.now() - timezone.timedelta(minutes=10)
            ).count()
            
            if recent_violations >= 5:
                # Flag attempt for review
                attempt.status = 'flagged'
                attempt.save()
                
                return JsonResponse({
                    'success': True,
                    'warning': 'Multiple violations detected. Test flagged for review.'
                })
        
        return JsonResponse({'success': True, 'event_id': event.id})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def test_consent_form(request, test_id):
    """
    Display consent form before starting test
    """
    from .models import Test
    test = get_object_or_404(Test, id=test_id, is_active=True)
    
    if request.method == 'POST':
        # User agreed to consent
        consent_given = request.POST.get('consent') == 'agree'
        
        if consent_given:
            # Create test attempt
            attempt = TestAttempt.objects.create(
                user=request.user,
                test=test,
                consent_given=True,
                consent_timestamp=timezone.now(),
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                status='in_progress'
            )
            
            # Generate random question set if auto-generate enabled
            if test.auto_generate_from_topics:
                questions = test.generate_question_set()
                attempt.question_set = [q.id for q in questions]
                attempt.save()
            
            # Redirect to test
            from django.urls import reverse
            return redirect(reverse('take_test', args=[attempt.id]))
        else:
            messages.error(request, 'You must agree to the consent terms to take the test.')
            return redirect('test_detail', test_id=test.id)
    
    return render(request, 'assessment/consent_form.html', {
        'test': test
    })