# UPDATED assessment/proctoring_views.py
# Replace the entire file with this version

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
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
    
    snapshot_file = request.FILES.get('snapshot')
    snapshot_type = request.POST.get('snapshot_type', 'webcam')  # webcam or screen
    
    if not snapshot_file:
        return JsonResponse({'error': 'No snapshot provided'}, status=400)
    
    try:
        # Open and compress image
        img = Image.open(snapshot_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Resize to max 640x480 to ensure ~200KB
        max_size = (640, 480)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save to BytesIO with JPEG compression
        output = BytesIO()
        img.save(output, format='JPEG', quality=70, optimize=True)
        output.seek(0)
        
        # Determine severity based on snapshot type
        severity = 'info'  # Normal snapshots are just info
        
        # Create proctoring event
        event = ProctoringEvent.objects.create(
            attempt=attempt,
            event_type=snapshot_type,  # 'webcam' or 'screen'
            severity=severity,
            metadata={
                'original_size': snapshot_file.size,
                'compressed_size': output.tell(),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': get_client_ip(request),
            }
        )
        
        # Save compressed image
        filename = f"{snapshot_type}_{attempt.user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
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
    Log proctoring events (tab switch, right-click, camera disabled, IP, etc.)
    UPDATED: Comprehensive event logging with severity levels
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        event_type = data.get('event_type')
        metadata = data.get('metadata', {})
        
        if not event_type:
            return JsonResponse({'error': 'Event type required'}, status=400)
        
        # Add request metadata
        metadata.update({
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'ip_address': get_client_ip(request),
            'timestamp': data.get('timestamp', timezone.now().isoformat()),
        })
        
        # Determine severity based on event type
        severity = determine_event_severity(event_type, metadata)
        
        # Special handling for IP address logging
        if event_type == 'ip_logged' and 'ip' in metadata:
            # Save IP to TestAttempt model
            if not attempt.ip_address:  # Only update if not already set
                attempt.ip_address = metadata['ip']
                attempt.save(update_fields=['ip_address'])
        
        # Special handling for camera disabled - flag attempt
        if event_type == 'camera_disabled':
            attempt.status = 'flagged'
            attempt.save(update_fields=['status'])
        
        # Create proctoring event
        event = ProctoringEvent.objects.create(
            attempt=attempt,
            event_type=event_type,
            severity=severity,
            metadata=metadata
        )
        
        return JsonResponse({
            'success': True, 
            'event_id': event.id,
            'severity': severity
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        # Log error but don't break the test
        print(f"Proctoring event error: {str(e)}")
        return JsonResponse({
            'success': False, 
            'error': 'Event logging failed',
            'details': str(e)
        }, status=400)


@login_required
def test_consent_form(request, test_id):
    """
    Display consent form before starting test
    UPDATED: Log consent acceptance as proctoring event
    """
    from .models import Test
    from django.urls import reverse
    from django.contrib import messages
    
    test = get_object_or_404(Test, id=test_id, is_active=True)
    
    if request.method == 'POST':
        # User agreed to consent
        consent_given = request.POST.get('consent') == 'agree'
        
        if consent_given:
            # Get client IP
            client_ip = get_client_ip(request)
            
            # Create test attempt with consent data
            attempt = TestAttempt.objects.create(
                user=request.user,
                test=test,
                consent_given=True,
                consent_timestamp=timezone.now(),
                ip_address=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                status='in_progress'
            )
            
            # Log consent acceptance as proctoring event
            ProctoringEvent.objects.create(
                attempt=attempt,
                event_type='consent_accepted',
                severity='info',
                metadata={
                    'ip_address': client_ip,
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'consent_timestamp': timezone.now().isoformat(),
                }
            )
            
            # Generate random question set if auto-generate enabled
            if test.auto_generate_from_topics:
                questions = test.generate_question_set()
                attempt.question_set = [q.id for q in questions]
                attempt.save()
            
            messages.success(request, 'Consent accepted. You may now begin the test.')
            
            # Redirect to test
            return redirect(reverse('take_test', args=[attempt.id]))
        else:
            messages.error(request, 'You must agree to the consent terms to take the test.')
            return redirect('test_detail', test_id=test.id)
    
    return render(request, 'assessment/consent_form.html', {
        'test': test
    })


def get_client_ip(request):
    """
    Get client IP address from request
    Handles proxies and X-Forwarded-For header
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def determine_event_severity(event_type, metadata):
    """
    Determine severity level based on event type
    Returns: 'info', 'warning', or 'critical'
    """
    # Critical events - serious violations
    critical_events = [
        'camera_disabled',
        'camera_permission_denied',
    ]
    
    # Warning events - potential issues
    warning_events = [
        'tab_switch',
        'fullscreen_exit',
        'window_blur',
    ]
    
    # Check if explicitly set in metadata
    if 'severity' in metadata:
        return metadata['severity']
    
    # Determine based on event type
    if event_type in critical_events:
        return 'critical'
    elif event_type in warning_events:
        # Escalate to critical if too many warnings
        warning_count = metadata.get('warning_count', 0)
        if warning_count >= 3:
            return 'critical'
        return 'warning'
    else:
        return 'info'
