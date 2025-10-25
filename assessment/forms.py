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
