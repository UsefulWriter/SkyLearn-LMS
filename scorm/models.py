import json
import os
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from course.models import Course
from core.utils import unique_slug_generator


def scorm_package_path(instance, filename):
    """Generate upload path for SCORM packages"""
    return f'scorm_packages/{instance.course.id}/{filename}'


def validate_scorm_package(file):
    """Validate that the uploaded file is a valid SCORM package"""
    if not file.name.endswith('.zip'):
        raise ValidationError(_('File must be a ZIP archive'))
    
    # Check file size (max 500MB)
    if file.size > 500 * 1024 * 1024:
        raise ValidationError(_('File size cannot exceed 500MB'))
    
    # Basic validation - check for manifest
    try:
        with zipfile.ZipFile(file, 'r') as zip_file:
            if 'imsmanifest.xml' not in zip_file.namelist():
                raise ValidationError(_('Invalid SCORM package: imsmanifest.xml not found'))
    except zipfile.BadZipFile:
        raise ValidationError(_('Invalid ZIP file'))


class ScormPackage(models.Model):
    """SCORM package model for storing SCORM content"""
    
    SCORM_VERSIONS = (
        ('1.2', 'SCORM 1.2'),
        ('2004', 'SCORM 2004 (3rd/4th Edition)'),
    )
    
    STATUS_CHOICES = (
        ('pending', _('Pending Processing')),
        ('processing', _('Processing')),
        ('ready', _('Ready')),
        ('error', _('Error')),
    )
    
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE,
        related_name='scorm_packages'
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    version = models.CharField(
        max_length=10, 
        choices=SCORM_VERSIONS,
        default='1.2',
        help_text=_('SCORM version of the package')
    )
    package_file = models.FileField(
        upload_to=scorm_package_path,
        validators=[
            FileExtensionValidator(['zip']),
            validate_scorm_package
        ],
        help_text=_('SCORM package ZIP file (max 500MB)')
    )
    extracted_path = models.CharField(
        max_length=500, 
        blank=True,
        help_text=_('Path where the package is extracted')
    )
    entry_point = models.CharField(
        max_length=255,
        blank=True,
        help_text=_('Launch URL from manifest')
    )
    manifest_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Parsed manifest data')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    error_message = models.TextField(blank=True)
    
    # Settings
    allow_multiple_attempts = models.BooleanField(
        default=True,
        help_text=_('Allow users to attempt this package multiple times')
    )
    passing_score = models.IntegerField(
        default=70,
        help_text=_('Minimum score to pass (percentage)')
    )
    weight_in_course = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text=_('Weight of this SCORM package in overall course grade (0-100%)')
    )
    
    # Metadata
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_scorm_packages'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('SCORM Package')
        verbose_name_plural = _('SCORM Packages')
    
    def __str__(self):
        return f"{self.title} - {self.course.title}"
    
    def get_absolute_url(self):
        return reverse('scorm:package_detail', kwargs={'slug': self.slug})
    
    def get_launch_url(self):
        """Get the URL to launch this SCORM package"""
        return reverse('scorm:launch', kwargs={'slug': self.slug})
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug_generator(self)
        super().save(*args, **kwargs)
    
    def extract_package(self):
        """Extract the SCORM package to the media directory"""
        if not self.package_file:
            return False
        
        # Create extraction directory
        extract_base = Path(settings.MEDIA_ROOT) / 'scorm_extracted' / str(self.course.id) / self.slug
        extract_base.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(self.package_file.path, 'r') as zip_file:
                zip_file.extractall(extract_base)
            
            self.extracted_path = str(extract_base.relative_to(settings.MEDIA_ROOT))
            
            # Parse manifest to find entry point
            manifest_path = extract_base / 'imsmanifest.xml'
            if manifest_path.exists():
                # Basic parsing - in production, use proper XML parser
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Simple regex to find the launch file
                    import re
                    match = re.search(r'<resource[^>]*href="([^"]+)"', content)
                    if match:
                        self.entry_point = match.group(1)
                    else:
                        self.entry_point = 'index.html'  # Default fallback
            
            self.status = 'ready'
            self.save()
            return True
            
        except Exception as e:
            self.status = 'error'
            self.error_message = str(e)
            self.save()
            return False


class ScormAttempt(models.Model):
    """Track user attempts at SCORM packages"""
    
    STATUS_CHOICES = (
        ('browsed', _('Browsed')),
        ('incomplete', _('Incomplete')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('passed', _('Passed')),
        ('not_attempted', _('Not Attempted')),
    )
    
    package = models.ForeignKey(
        ScormPackage,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scorm_attempts'
    )
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # SCORM data
    lesson_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_attempted'
    )
    score_raw = models.FloatField(null=True, blank=True)
    score_min = models.FloatField(default=0)
    score_max = models.FloatField(default=100)
    score_scaled = models.FloatField(null=True, blank=True)
    
    # Progress tracking
    progress_measure = models.FloatField(default=0)
    total_time = models.DurationField(null=True, blank=True)
    session_time = models.DurationField(null=True, blank=True)
    
    # Suspend data for resuming
    suspend_data = models.TextField(blank=True)
    lesson_location = models.CharField(max_length=255, blank=True)
    
    # Additional tracking
    exit_mode = models.CharField(max_length=20, blank=True)
    credit = models.CharField(max_length=20, default='credit')
    entry = models.CharField(max_length=20, default='ab-initio')
    
    class Meta:
        ordering = ['-started_at']
        unique_together = [['package', 'user', 'started_at']]
        verbose_name = _('SCORM Attempt')
        verbose_name_plural = _('SCORM Attempts')
    
    def __str__(self):
        return f"{self.user.username} - {self.package.title} - {self.lesson_status}"
    
    def is_passed(self):
        """Check if the attempt passed based on package settings"""
        if self.score_raw is not None and self.package.passing_score:
            percentage = (self.score_raw / self.score_max) * 100 if self.score_max else 0
            return percentage >= self.package.passing_score
        return self.lesson_status == 'passed'
    
    def get_percentage_score(self):
        """Get the score as a percentage"""
        if self.score_raw is not None and self.score_max:
            return (self.score_raw / self.score_max) * 100
        return 0


class ScormInteraction(models.Model):
    """Track detailed interactions within SCORM content"""
    
    INTERACTION_TYPES = (
        ('true-false', 'True/False'),
        ('choice', 'Multiple Choice'),
        ('fill-in', 'Fill In'),
        ('long-fill-in', 'Long Fill In'),
        ('matching', 'Matching'),
        ('performance', 'Performance'),
        ('sequencing', 'Sequencing'),
        ('likert', 'Likert'),
        ('numeric', 'Numeric'),
        ('other', 'Other'),
    )
    
    RESULT_CHOICES = (
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect'),
        ('unanticipated', 'Unanticipated'),
        ('neutral', 'Neutral'),
    )
    
    attempt = models.ForeignKey(
        ScormAttempt,
        on_delete=models.CASCADE,
        related_name='interactions'
    )
    interaction_id = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Responses
    correct_responses = models.JSONField(default=list)
    learner_response = models.TextField()
    result = models.CharField(max_length=20, choices=RESULT_CHOICES)
    
    # Scoring
    weighting = models.FloatField(default=1.0)
    latency = models.DurationField(null=True, blank=True)
    
    # Additional data
    description = models.TextField(blank=True)
    objectives = models.JSONField(default=list)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = _('SCORM Interaction')
        verbose_name_plural = _('SCORM Interactions')
    
    def __str__(self):
        return f"{self.attempt} - {self.interaction_id}"


class ScormObjective(models.Model):
    """Track learning objectives within SCORM content"""
    
    STATUS_CHOICES = (
        ('not_satisfied', 'Not Satisfied'),
        ('satisfied', 'Satisfied'),
        ('unknown', 'Unknown'),
    )
    
    attempt = models.ForeignKey(
        ScormAttempt,
        on_delete=models.CASCADE,
        related_name='objectives'
    )
    objective_id = models.CharField(max_length=255)
    
    # Status tracking
    success_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unknown'
    )
    completion_status = models.CharField(
        max_length=20,
        choices=ScormAttempt.STATUS_CHOICES,
        default='not_attempted'
    )
    
    # Scoring
    score_raw = models.FloatField(null=True, blank=True)
    score_min = models.FloatField(default=0)
    score_max = models.FloatField(default=100)
    score_scaled = models.FloatField(null=True, blank=True)
    
    # Progress
    progress_measure = models.FloatField(default=0)
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = [['attempt', 'objective_id']]
        verbose_name = _('SCORM Objective')
        verbose_name_plural = _('SCORM Objectives')
    
    def __str__(self):
        return f"{self.attempt} - {self.objective_id}"
