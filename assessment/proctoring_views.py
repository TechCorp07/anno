# UPDATED assessment/proctoring_views.py
# Replace the entire file with this version

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from PIL import Image
from io import BytesIO
import json
import cv2
import numpy as np

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: face_recognition not installed. Face verification disabled.")

from .models import TestAttempt, ProctoringEvent


# ============ DEVICE DETECTION ============

def is_mobile_device(user_agent):
    """
    Detect if device is mobile or tablet
    Returns: (is_mobile, device_type)
    """
    if not user_agent:
        return False, 'unknown'
    
    user_agent = user_agent.lower()
    
    # Mobile indicators
    mobile_keywords = [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 
        'blackberry', 'windows phone', 'webos'
    ]
    
    # Tablet indicators
    tablet_keywords = ['tablet', 'ipad', 'playbook', 'silk']
    
    # Check tablet first (more specific)
    for keyword in tablet_keywords:
        if keyword in user_agent:
            return True, 'tablet'
    
    # Check mobile
    for keyword in mobile_keywords:
        if keyword in user_agent:
            return True, 'mobile'
    
    return False, 'desktop'


@login_required
def check_device_compatibility(request, test_id):
    """
    NEW: Check if device is allowed to take test
    Called before consent form
    """
    from .models import Test
    
    test = get_object_or_404(Test, id=test_id, is_active=True)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    is_mobile, device_type = is_mobile_device(user_agent)
    
    # Check if mobile devices are blocked
    block_mobile = getattr(settings, 'BLOCK_MOBILE_DEVICES', True)
    
    if block_mobile and is_mobile:
        # Log blocked attempt
        attempt = TestAttempt.objects.create(
            user=request.user,
            test=test,
            status='blocked',
            user_agent=user_agent,
            ip_address=get_client_ip(request)
        )
        
        ProctoringEvent.objects.create(
            attempt=attempt,
            event_type='mobile_device_blocked',
            severity='warning',
            metadata={
                'device_type': device_type,
                'user_agent': user_agent,
                'ip_address': get_client_ip(request)
            }
        )
        
        return render(request, 'assessment/device_blocked.html', {
            'test': test,
            'device_type': device_type,
            'allowed_devices': 'desktop or laptop computers'
        })
    
    # Device is allowed - log verification and proceed to consent
    return redirect('test_consent', test_id=test.id)


# ============ FACE VERIFICATION ============

def calculate_blur_score(image_array):
    """
    Calculate blur score using Laplacian variance
    Higher score = sharper image
    Score < 50 typically means blurry
    """
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return laplacian_var


def verify_face_clarity(image_file):
    """
    NEW: Verify that candidate's face is clear and detectable
    Returns: (success, message, metadata)
    """
    if not FACE_RECOGNITION_AVAILABLE:
        return True, "Face verification disabled", {'skipped': True}
    
    if not getattr(settings, 'FACE_VERIFICATION_ENABLED', True):
        return True, "Face verification disabled", {'skipped': True}
    
    try:
        # Load image
        img = Image.open(image_file)
        img_array = np.array(img)
        
        # Convert to RGB if needed
        if len(img_array.shape) == 2:  # Grayscale
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2RGB)
        elif img_array.shape[2] == 4:  # RGBA
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
        
        # 1. Detect faces
        face_locations = face_recognition.face_locations(img_array, model='hog')
        
        if len(face_locations) == 0:
            return False, "No face detected. Please position yourself clearly in front of the camera.", {
                'error': 'no_face_detected',
                'faces_found': 0
            }
        
        if len(face_locations) > 1:
            return False, "Multiple faces detected. Please ensure only you are visible.", {
                'error': 'multiple_faces',
                'faces_found': len(face_locations)
            }
        
        # 2. Check face size
        top, right, bottom, left = face_locations[0]
        face_width = right - left
        face_height = bottom - top
        min_size = getattr(settings, 'MIN_FACE_SIZE_PIXELS', 100)
        
        if face_width < min_size or face_height < min_size:
            return False, "Face too small. Please move closer to the camera.", {
                'error': 'face_too_small',
                'face_width': face_width,
                'face_height': face_height,
                'min_required': min_size
            }
        
        # 3. Check blur/clarity
        blur_score = calculate_blur_score(img_array)
        min_clarity = getattr(settings, 'MIN_FACE_CLARITY_SCORE', 50)
        
        if blur_score < min_clarity:
            return False, "Image too blurry. Please ensure good lighting and a steady camera.", {
                'error': 'image_too_blurry',
                'blur_score': blur_score,
                'min_required': min_clarity
            }
        
        # All checks passed
        return True, "Face verification successful", {
            'faces_found': 1,
            'face_width': face_width,
            'face_height': face_height,
            'blur_score': blur_score,
            'quality': 'good' if blur_score > 100 else 'acceptable'
        }
        
    except Exception as e:
        print(f"Face verification error: {str(e)}")
        # Don't block test on verification errors, but log them
        return True, "Face verification skipped due to error", {
            'error': str(e),
            'skipped': True
        }


@login_required
@require_http_methods(["POST"])
def verify_candidate_face(request, attempt_id):
    """
    NEW: Verify candidate's face before starting test
    Called from consent page with initial webcam snapshot
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    face_image = request.FILES.get('face_snapshot')
    if not face_image:
        return JsonResponse({
            'success': False,
            'error': 'No image provided'
        }, status=400)
    
    # Verify face clarity
    success, message, metadata = verify_face_clarity(face_image)
    
    # Log verification attempt
    event_type = 'face_verification_passed' if success else 'face_verification_failed'
    severity = 'info' if success else 'warning'
    
    # Save verification snapshot
    event = ProctoringEvent.objects.create(
        attempt=attempt,
        event_type=event_type,
        severity=severity,
        metadata=metadata
    )
    
    # Save the image
    if success:
        filename = f"face_verification_{attempt.user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        event.image_file.save(filename, face_image, save=True)
    
    return JsonResponse({
        'success': success,
        'message': message,
        'metadata': metadata,
        'can_proceed': success
    })


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
    
    is_event_screenshot = snapshot_type.startswith('event_')
    event_metadata_json = request.POST.get('event_metadata')
    
    if not snapshot_file:
        return JsonResponse({'error': 'No snapshot provided'}, status=400)
    
    try:
            # Compress image
            img = Image.open(snapshot_file)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            max_size = (640, 480)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            output = BytesIO()
            img.save(output, format='JPEG', quality=70, optimize=True)
            output.seek(0)
            
            # Parse event metadata if present
            event_metadata = None
            if event_metadata_json:
                try:
                    event_metadata = json.loads(event_metadata_json)
                except json.JSONDecodeError:
                    event_metadata = {}
            
            # Determine severity
            severity = 'info'
            if is_event_screenshot:
                if event_metadata and event_metadata.get('severity'):
                    severity = event_metadata['severity']
                else:
                    severity = 'warning'  # Default for event screenshots
            
            # Create proctoring event
            event = ProctoringEvent.objects.create(
                attempt=attempt,
                event_type=snapshot_type,
                severity=severity,
                is_event_screenshot=is_event_screenshot,
                event_metadata=event_metadata,
                metadata={
                    'original_size': snapshot_file.size,
                    'compressed_size': output.tell(),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'ip_address': get_client_ip(request),
                    'is_event': is_event_screenshot
                }
            )
            
            # Save compressed image
            filename = f"{snapshot_type}_{attempt.user.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            event.image_file.save(filename, ContentFile(output.read()), save=True)
            
            return JsonResponse({
                'success': True,
                'event_id': event.id,
                'is_event_screenshot': is_event_screenshot,
                'severity': severity
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def log_proctoring_event(request, attempt_id):
    """
    UPDATED: Enhanced event logging with away time tracking
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
        
        # Determine severity
        severity = determine_event_severity(event_type, metadata)
        
        # Special handling for IP logging
        if event_type == 'ip_logged' and 'ip' in metadata:
            if not attempt.ip_address:
                attempt.ip_address = metadata['ip']
                attempt.save(update_fields=['ip_address'])
        
        # Special handling for camera disabled
        if event_type == 'camera_disabled':
            attempt.status = 'flagged'
            attempt.save(update_fields=['status'])
        
        # Create event
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
        print(f"Proctoring event error: {str(e)}")
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=400)


@login_required
def test_consent_form(request, test_id):
    """
    Display consent form before starting test
    FIXED: Create attempt BEFORE showing consent form so face verification has attempt_id
    """
    from .models import Test
    from django.urls import reverse
    from django.contrib import messages
    
    test = get_object_or_404(Test, id=test_id, is_active=True)
    
    if request.method == 'POST':
        # User submitted consent form
        consent_given = request.POST.get('consent') == 'agree'
        face_verified = request.POST.get('face_verified') == 'true'
        
        # Get the attempt that was created on GET
        attempt_id = request.POST.get('attempt_id')
        if not attempt_id:
            messages.error(request, 'Invalid attempt. Please try again.')
            return redirect('test_detail', test_id=test.id)
        
        attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
        
        if consent_given and face_verified:
            # Update attempt with consent data
            attempt.consent_given = True
            attempt.consent_timestamp = timezone.now()
            attempt.status = 'in_progress'
            attempt.started_at = timezone.now()
            
            attempt.save()
            
            # Log consent acceptance as proctoring event
            ProctoringEvent.objects.create(
                attempt=attempt,
                event_type='consent_accepted',
                severity='info',
                metadata={
                    'ip_address': attempt.ip_address,
                    'user_agent': attempt.user_agent,
                    'consent_timestamp': timezone.now().isoformat(),
                    'face_verified': True,
                    'test_start_time': timezone.now().isoformat()
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
            # Delete the attempt if consent not given
            attempt.delete()
            messages.error(request, 'You must complete face verification and agree to the consent terms to take the test.')
            return redirect('test_detail', test_id=test.id)
    
    # GET request - Create attempt NOW (before showing consent form)
    # This allows face verification to have an attempt_id
    client_ip = get_client_ip(request)
    
    # Check if user already has a pending attempt for this test
    existing_attempt = TestAttempt.objects.filter(
        user=request.user,
        test=test,
        consent_given=False,
        status='started'
    ).first()
    
    if existing_attempt:
        # Reuse existing pending attempt
        attempt = existing_attempt
    else:
        # Create new pending attempt
        attempt = TestAttempt.objects.create(
            user=request.user,
            test=test,
            consent_given=False,
            consent_timestamp=None,
            ip_address=client_ip,
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            status='started',  # Will change to 'in_progress' after consent
            started_at=None
        )
    
    return render(request, 'assessment/consent_form.html', {
        'test': test,
        'attempt': attempt  # NOW PASSED TO TEMPLATE!
    })


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def determine_event_severity(event_type, metadata):
    """
    UPDATED: Enhanced severity determination with away time consideration
    """
    critical_events = [
        'camera_disabled',
        'camera_permission_denied',
        'face_verification_failed',
        'no_face_detected',
    ]
    
    warning_events = [
        'tab_switched',
        'fullscreen_exit',
        'window_blur',
        'copy_paste_blocked',
        'event_tab_switch',
        'event_window_blur',
        'event_fullscreen_exit',
        'event_copy_paste_attempt',
    ]
    
    # Check explicit severity
    if 'severity' in metadata:
        return metadata['severity']
    
    # Critical events
    if event_type in critical_events:
        return 'critical'
    
    # Warning events with escalation
    if event_type in warning_events:
        warning_count = metadata.get('warning_count', 0)
        away_time = metadata.get('away_time_seconds', 0)
        
        # Escalate to critical if too many warnings or away too long
        if warning_count >= 3 or away_time > 60:
            return 'critical'
        return 'warning'
    
    return 'info'


@staff_member_required
def view_candidate_images(request, attempt_id):
    """
    UPDATED: Enhanced gallery with event screenshots highlighted
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id)
    
    # Get periodic snapshots
    webcam_images = attempt.proctoring_events.filter(
        event_type='webcam',
        image_file__isnull=False
    ).order_by('timestamp')
    
    screen_images = attempt.proctoring_events.filter(
        event_type='screen',
        image_file__isnull=False
    ).order_by('timestamp')
    
    # NEW: Get event-triggered screenshots
    event_screenshots = attempt.proctoring_events.filter(
        is_event_screenshot=True,
        image_file__isnull=False
    ).order_by('timestamp')
    
    # Get critical events
    critical_events = attempt.proctoring_events.filter(
        severity='critical'
    ).order_by('timestamp')
    
    # NEW: Get away time summary
    away_events = attempt.proctoring_events.filter(
        event_type__in=['tab_returned', 'window_focus_returned']
    )
    total_away_time = sum([
        e.metadata.get('away_time_seconds', 0) 
        for e in away_events 
        if e.metadata
    ])
    
    context = {
        'attempt': attempt,
        'candidate': attempt.user,
        'test': attempt.test,
        'webcam_images': webcam_images,
        'screen_images': screen_images,
        'event_screenshots': event_screenshots,
        'critical_events': critical_events,
        'total_images': webcam_images.count() + screen_images.count() + event_screenshots.count(),
        'total_away_time_minutes': round(total_away_time / 60, 1),
    }
    
    return render(request, 'proctoring/candidate_images.html', context)

