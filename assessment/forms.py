from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile
from django.utils import timezone

class CandidateRegistrationForm(UserCreationForm):
    """
    Enhanced registration form for MRI Technician candidates
    Collects comprehensive information during signup
    """
    
    # User Model Fields
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'Enter your first name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'Enter your last name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'your.email@example.com'
        })
    )
    
    # UserProfile Fields - Personal Info
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': '+263771234567 or 0771234567'
        })
    )
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'type': 'date'
        })
    )
    national_id = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': '63-123456A63'
        })
    )
    gender = forms.ChoiceField(
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say')
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
        })
    )
    
    # Location
    province = forms.ChoiceField(
        choices=[
            ('', 'Select your province'),
            ('harare', 'Harare'),
            ('bulawayo', 'Bulawayo'),
            ('manicaland', 'Manicaland'),
            ('mashonaland_central', 'Mashonaland Central'),
            ('mashonaland_east', 'Mashonaland East'),
            ('mashonaland_west', 'Mashonaland West'),
            ('masvingo', 'Masvingo'),
            ('matabeleland_north', 'Matabeleland North'),
            ('matabeleland_south', 'Matabeleland South'),
            ('midlands', 'Midlands'),
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
        })
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'Your city or town'
        })
    )
    
    street_address = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'e.g., 123 Main Street, Apartment 4B'
        }),
        help_text='Your full street address'
    )
    
    suburb = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'e.g., Avondale, Borrowdale'
        }),
        help_text='Suburb or neighborhood (optional)'
    )
    
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'Postal code (optional)'
        })
    )
    
    cv_document = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100',
            'accept': '.pdf,.docx'
        }),
        help_text='Upload your CV/Resume in PDF or DOCX format (Max 5MB)'
    )
    
    # Professional Information
    employment_status = forms.ChoiceField(
        choices=[
            ('', 'Select employment status'),
            ('employed', 'Currently Employed'),
            ('unemployed', 'Unemployed'),
            ('student', 'Student'),
            ('self_employed', 'Self-Employed')
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
        })
    )
    current_employer = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'Hospital or institution name (optional)'
        })
    )
    years_of_experience = forms.ChoiceField(
        choices=[
            ('0', 'No Experience'),
            ('1-2', '1-2 years'),
            ('3-5', '3-5 years'),
            ('5+', 'More than 5 years')
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
        })
    )
    has_mri_experience = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-green-600 border-gray-300 rounded focus:ring-green-500'
        })
    )
    education_level = forms.ChoiceField(
        choices=[
            ('', 'Select your education level'),
            ('diploma', 'Diploma in Radiography'),
            ('degree', 'Degree in Radiography'),
            ('masters', 'Masters in Medical Imaging'),
            ('other', 'Other Medical Background')
        ],
        required=True,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent'
        })
    )
    institution_attended = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'University or college name (optional)'
        })
    )
    
    # License Information
    radiography_license_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'Your license/registration number (if applicable)'
        })
    )
    
    # Consents
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-green-600 border-gray-300 rounded focus:ring-green-500'
        }),
        label='I accept the Terms and Conditions'
    )
    data_processing_consent = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 text-green-600 border-gray-300 rounded focus:ring-green-500'
        }),
        label='I consent to the processing of my personal data'
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add custom styling to password fields
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'Create a strong password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent',
            'placeholder': 'Confirm your password'
        })
    
    def clean_email(self):
        """Validate that email is unique"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email
    
    def clean_national_id(self):
        """Validate that national ID is unique"""
        national_id = self.cleaned_data.get('national_id')
        if UserProfile.objects.filter(national_id=national_id).exists():
            raise forms.ValidationError("This National ID is already registered.")
        return national_id
    
    def clean_cv_document(self):
        """Validate CV file size and type"""
        cv_file = self.cleaned_data.get('cv_document')
        
        if cv_file:
            # Check file size (5MB limit)
            if cv_file.size > 5 * 1024 * 1024:  # 5MB in bytes
                raise forms.ValidationError("CV file size must be under 5MB.")
            
            # Check file extension
            import os
            ext = os.path.splitext(cv_file.name)[1].lower()
            if ext not in ['.pdf', '.docx']:
                raise forms.ValidationError("Only PDF and DOCX files are allowed.")
        
        return cv_file
    
    def save(self, commit=True):
        """Save user and create profile with all additional fields"""
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Create or update user profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Personal Information
            profile.phone_number = self.cleaned_data['phone_number']
            profile.date_of_birth = self.cleaned_data['date_of_birth']
            profile.national_id = self.cleaned_data['national_id']
            profile.gender = self.cleaned_data['gender']
            
            # Location
            profile.province = self.cleaned_data['province']
            profile.city = self.cleaned_data['city']
            profile.street_address = self.cleaned_data['street_address']
            profile.suburb = self.cleaned_data.get('suburb', '')
            profile.postal_code = self.cleaned_data.get('postal_code', '')
            
            # CV Upload
            if self.cleaned_data.get('cv_document'):
                profile.cv_document = self.cleaned_data['cv_document']
                profile.cv_uploaded_at = timezone.now()
                
            # Professional Information
            profile.employment_status = self.cleaned_data['employment_status']
            profile.current_employer = self.cleaned_data.get('current_employer', '')
            profile.years_of_experience = self.cleaned_data['years_of_experience']
            profile.has_mri_experience = self.cleaned_data.get('has_mri_experience', False)
            profile.education_level = self.cleaned_data['education_level']
            profile.institution_attended = self.cleaned_data.get('institution_attended', '')
            profile.radiography_license_number = self.cleaned_data.get('radiography_license_number', '')
            
            # Consents
            profile.terms_accepted = self.cleaned_data['terms_accepted']
            profile.terms_accepted_at = timezone.now() if self.cleaned_data['terms_accepted'] else None
            profile.data_processing_consent = self.cleaned_data['data_processing_consent']
            profile.data_consent_at = timezone.now() if self.cleaned_data['data_processing_consent'] else None
            
            profile.save()
        
        return user


class UserProfileUpdateForm(forms.ModelForm):
    """
    Form for existing users to update their profile information
    Allows updating CV and address without re-registering
    """
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'date_of_birth', 'gender',
            'street_address', 'suburb', 'city', 'province', 'postal_code',
            'cv_document',
            'employment_status', 'current_employer', 'years_of_experience',
            'has_mri_experience', 'education_level', 'institution_attended',
            'radiography_license_number', 'profile_photo'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': '+263771234567'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'street_address': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': '123 Main Street'
            }),
            'suburb': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Suburb name'
            }),
            'city': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'City/Town'
            }),
            'province': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Postal code'
            }),
            'cv_document': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': '.pdf,.docx'
            }),
            'employment_status': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'current_employer': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'years_of_experience': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'has_mri_experience': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
            }),
            'education_level': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'institution_attended': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'radiography_license_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'profile_photo': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*'
            }),
        }
    
    def clean_cv_document(self):
        """Validate CV file size and type"""
        cv_file = self.cleaned_data.get('cv_document')
        
        if cv_file:
            # Check file size (5MB limit)
            if cv_file.size > 5 * 1024 * 1024:
                raise forms.ValidationError("CV file size must be under 5MB.")
            
            # Check file extension
            import os
            ext = os.path.splitext(cv_file.name)[1].lower()
            if ext not in ['.pdf', '.docx']:
                raise forms.ValidationError("Only PDF and DOCX files are allowed.")
        
        return cv_file
    
    def save(self, commit=True):
        """Save profile and update CV timestamp if new CV uploaded"""
        profile = super().save(commit=False)
        
        # Update CV timestamp if new CV was uploaded
        if self.cleaned_data.get('cv_document') and self.has_changed() and 'cv_document' in self.changed_data:
            profile.cv_uploaded_at = timezone.now()
        
        if commit:
            profile.save()
        
        return profile

