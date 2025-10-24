"""
Utility functions for the assessment app
"""
from django.utils import timezone
from assessment.models import TestAttempt


def create_test_attempts_bulk(test, users):
    """
    Create test attempts for multiple users efficiently.
    
    Usage:
        from assessment.utils import create_test_attempts_bulk
        
        users = User.objects.filter(cohort=my_cohort)
        attempts = create_test_attempts_bulk(test, users)
    
    Args:
        test: Test instance
        users: QuerySet or list of User instances
    
    Returns:
        List of created TestAttempt instances
    """
    attempts = []
    for user in users:
        attempt = TestAttempt(
            user=user,
            test=test,
            status='started',
            consent_given=False,
            started_at=timezone.now()
        )
        attempts.append(attempt)
    
    # Single query instead of N queries!
    created_attempts = TestAttempt.objects.bulk_create(attempts)
    
    # Generate questions for each attempt
    for attempt in created_attempts:
        if test.auto_generate_from_topics:
            questions = test.generate_question_set()
            attempt.question_set = [q.id for q in questions]
    
    # Bulk update
    TestAttempt.objects.bulk_update(created_attempts, ['question_set'])
    
    return created_attempts
