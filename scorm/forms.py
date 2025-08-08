from django import forms
from django.utils.translation import gettext_lazy as _

from course.models import Course
from .models import ScormPackage


class ScormPackageUploadForm(forms.ModelForm):
    """Form for uploading SCORM packages"""
    
    class Meta:
        model = ScormPackage
        fields = [
            'title',
            'description', 
            'course',
            'version',
            'package_file',
            'allow_multiple_attempts',
            'passing_score',
            'weight_in_course'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter SCORM package title')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Enter description (optional)')
            }),
            'course': forms.Select(attrs={
                'class': 'form-control'
            }),
            'version': forms.Select(attrs={
                'class': 'form-control'
            }),
            'package_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.zip'
            }),
            'allow_multiple_attempts': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'passing_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 1
            }),
            'weight_in_course': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 0.1
            })
        }
        
        labels = {
            'title': _('Package Title'),
            'description': _('Description'),
            'course': _('Course'),
            'version': _('SCORM Version'),
            'package_file': _('SCORM Package File'),
            'allow_multiple_attempts': _('Allow Multiple Attempts'),
            'passing_score': _('Passing Score (%)'),
            'weight_in_course': _('Weight in Course Grade (%)')
        }
        
        help_texts = {
            'package_file': _('Upload a ZIP file containing your SCORM package (max 500MB)'),
            'passing_score': _('Minimum score required to pass (0-100%)'),
            'weight_in_course': _('How much this package contributes to the overall course grade')
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Limit course choices to courses the user can manage
        if user and hasattr(user, 'is_superuser') and user.is_superuser:
            # Admins can see all courses
            self.fields['course'].queryset = Course.objects.all()
        elif user and hasattr(user, 'allocated_lecturer'):
            # Lecturers can only see their allocated courses
            allocated_courses = Course.objects.filter(
                allocated_course__lecturer=user
            ).distinct()
            self.fields['course'].queryset = allocated_courses
        else:
            # No courses available for other users
            self.fields['course'].queryset = Course.objects.none()
    
    def clean_package_file(self):
        """Additional validation for the package file"""
        package_file = self.cleaned_data.get('package_file')
        
        if not package_file:
            return package_file
        
        # Check file extension
        if not package_file.name.lower().endswith('.zip'):
            raise forms.ValidationError(_('Please upload a ZIP file.'))
        
        # Check file size (500MB limit)
        max_size = 500 * 1024 * 1024  # 500MB
        if package_file.size > max_size:
            raise forms.ValidationError(_('File size cannot exceed 500MB.'))
        
        return package_file
    
    def clean_passing_score(self):
        """Validate passing score range"""
        passing_score = self.cleaned_data.get('passing_score')
        
        if passing_score is not None:
            if not (0 <= passing_score <= 100):
                raise forms.ValidationError(_('Passing score must be between 0 and 100.'))
        
        return passing_score
    
    def clean_weight_in_course(self):
        """Validate weight in course range"""
        weight = self.cleaned_data.get('weight_in_course')
        
        if weight is not None:
            if not (0 <= weight <= 100):
                raise forms.ValidationError(_('Weight must be between 0 and 100.'))
        
        return weight


class ScormPackageEditForm(forms.ModelForm):
    """Form for editing SCORM package settings (without file upload)"""
    
    class Meta:
        model = ScormPackage
        fields = [
            'title',
            'description',
            'allow_multiple_attempts',
            'passing_score',
            'weight_in_course'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'allow_multiple_attempts': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'passing_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 1
            }),
            'weight_in_course': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'step': 0.1
            })
        }
    
    def clean_passing_score(self):
        """Validate passing score range"""
        passing_score = self.cleaned_data.get('passing_score')
        
        if passing_score is not None:
            if not (0 <= passing_score <= 100):
                raise forms.ValidationError(_('Passing score must be between 0 and 100.'))
        
        return passing_score
    
    def clean_weight_in_course(self):
        """Validate weight in course range"""
        weight = self.cleaned_data.get('weight_in_course')
        
        if weight is not None:
            if not (0 <= weight <= 100):
                raise forms.ValidationError(_('Weight must be between 0 and 100.'))
        
        return weight


class ScormPackageFilterForm(forms.Form):
    """Form for filtering SCORM packages"""
    
    STATUS_CHOICES = [('', _('All Statuses'))] + list(ScormPackage.STATUS_CHOICES)
    VERSION_CHOICES = [('', _('All Versions'))] + list(ScormPackage.SCORM_VERSIONS)
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search packages...')
        })
    )
    
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        required=False,
        empty_label=_('All Courses'),
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    version = forms.ChoiceField(
        choices=VERSION_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Limit course choices based on user permissions
        if user and hasattr(user, 'is_superuser') and user.is_superuser:
            # Admins can see all courses
            self.fields['course'].queryset = Course.objects.all()
        elif user and hasattr(user, 'allocated_lecturer'):
            # Lecturers can only see their allocated courses
            allocated_courses = Course.objects.filter(
                allocated_course__lecturer=user
            ).distinct()
            self.fields['course'].queryset = allocated_courses
        else:
            # Students and others can see all courses (for viewing purposes)
            self.fields['course'].queryset = Course.objects.all()