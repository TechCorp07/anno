"""
Context Processors for MRI Training Platform Assessment
Makes profile completion data available in all templates
"""

def profile_completion(request):
    """
    Make profile completion data available in all templates.
    
    This context processor adds profile completion information to the context
    of every template, allowing the base template and other templates to 
    display profile completion status without explicitly passing it in views.
    
    Returns:
        dict: Contains 'profile_completion' with percentage, completed_count,
              total_count, missing_fields, and is_complete status
    """
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            
            # Required fields for profile completion
            required_fields = {
                'phone_number': 'Phone Number',
                'date_of_birth': 'Date of Birth',
                'national_id': 'National ID',
                'province': 'Province',
                'city': 'City',
                'street_address': 'Street Address',
                'employment_status': 'Employment Status',
                'education_level': 'Education Level',
                'terms_accepted': 'Terms Accepted',
                'data_processing_consent': 'Data Processing Consent',
                'cv_document': 'CV Document',
            }
            
            completed_fields = []
            missing_fields = []
            
            for field, label in required_fields.items():
                value = getattr(profile, field, None)
                if value:
                    completed_fields.append(label)
                else:
                    missing_fields.append(label)
            
            total_count = len(required_fields)
            completed_count = len(completed_fields)
            percentage = int((completed_count / total_count) * 100)
            
            return {
                'profile_completion': {
                    'percentage': percentage,
                    'completed_count': completed_count,
                    'total_count': total_count,
                    'missing_fields': missing_fields,
                    'is_complete': percentage == 100
                }
            }
        except Exception as e:
            # If profile doesn't exist or any error occurs, return empty data
            # This prevents template errors
            return {
                'profile_completion': {
                    'percentage': 0,
                    'completed_count': 0,
                    'total_count': 11,
                    'missing_fields': [],
                    'is_complete': False
                }
            }
    
    # For non-authenticated users, return None
    return {
        'profile_completion': None
    }