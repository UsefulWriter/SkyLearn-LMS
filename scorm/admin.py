from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import ScormPackage, ScormAttempt, ScormInteraction, ScormObjective


@admin.register(ScormPackage)
class ScormPackageAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'course', 'version', 'status', 'uploaded_by', 
        'created_at', 'weight_in_course', 'passing_score'
    ]
    list_filter = ['status', 'version', 'course', 'created_at', 'allow_multiple_attempts']
    search_fields = ['title', 'description', 'course__title']
    readonly_fields = ['slug', 'extracted_path', 'entry_point', 'manifest_data', 'status', 'error_message']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('title', 'slug', 'description', 'course', 'version')
        }),
        (_('Package File'), {
            'fields': ('package_file', 'extracted_path', 'entry_point', 'status', 'error_message')
        }),
        (_('Settings'), {
            'fields': ('allow_multiple_attempts', 'passing_score', 'weight_in_course')
        }),
        (_('Technical Data'), {
            'fields': ('manifest_data',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('uploaded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj:  # editing existing object
            readonly.extend(['package_file', 'course', 'version'])
        readonly.extend(['created_at', 'updated_at'])
        return readonly
    
    def save_model(self, request, obj, form, change):
        if not change:  # creating new object
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
        
        # Extract package if new file uploaded
        if not change and obj.package_file:
            obj.extract_package()


class ScormInteractionInline(admin.TabularInline):
    model = ScormInteraction
    extra = 0
    readonly_fields = ['interaction_id', 'type', 'timestamp', 'result', 'learner_response']


class ScormObjectiveInline(admin.TabularInline):
    model = ScormObjective
    extra = 0
    readonly_fields = ['objective_id', 'success_status', 'completion_status', 'score_raw']


@admin.register(ScormAttempt)
class ScormAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'package', 'lesson_status', 'score_display', 
        'started_at', 'completed_at', 'is_passed'
    ]
    list_filter = [
        'lesson_status', 'package__course', 'package__version', 
        'started_at', 'completed_at'
    ]
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'package__title', 'package__course__title'
    ]
    readonly_fields = [
        'package', 'user', 'started_at', 'last_accessed', 'completed_at'
    ]
    
    fieldsets = (
        (_('Attempt Information'), {
            'fields': ('package', 'user', 'started_at', 'last_accessed', 'completed_at')
        }),
        (_('SCORM Data'), {
            'fields': (
                'lesson_status', 'score_raw', 'score_min', 'score_max', 
                'progress_measure', 'total_time', 'session_time'
            )
        }),
        (_('Suspend Data'), {
            'fields': ('suspend_data', 'lesson_location', 'exit_mode', 'credit', 'entry'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ScormInteractionInline, ScormObjectiveInline]
    
    def score_display(self, obj):
        if obj.score_raw is not None:
            percentage = obj.get_percentage_score()
            color = 'green' if percentage >= obj.package.passing_score else 'red'
            return format_html(
                '<span style="color: {};">{:.0f}%</span>',
                color, percentage
            )
        return '-'
    score_display.short_description = _('Score')
    
    def is_passed(self, obj):
        passed = obj.is_passed()
        if passed:
            return format_html('<span style="color: green;">✓</span>')
        elif obj.score_raw is not None:
            return format_html('<span style="color: red;">✗</span>')
        return '-'
    is_passed.short_description = _('Passed')
    is_passed.boolean = True


@admin.register(ScormInteraction)
class ScormInteractionAdmin(admin.ModelAdmin):
    list_display = [
        'attempt_user', 'attempt_package', 'interaction_id', 
        'type', 'result', 'timestamp'
    ]
    list_filter = [
        'type', 'result', 'timestamp', 'attempt__package__course'
    ]
    search_fields = [
        'interaction_id', 'description', 'learner_response',
        'attempt__user__username', 'attempt__package__title'
    ]
    readonly_fields = ['attempt', 'timestamp']
    
    def attempt_user(self, obj):
        return obj.attempt.user.get_full_name() or obj.attempt.user.username
    attempt_user.short_description = _('User')
    
    def attempt_package(self, obj):
        return obj.attempt.package.title
    attempt_package.short_description = _('Package')


@admin.register(ScormObjective)
class ScormObjectiveAdmin(admin.ModelAdmin):
    list_display = [
        'attempt_user', 'attempt_package', 'objective_id',
        'success_status', 'completion_status', 'score_raw'
    ]
    list_filter = [
        'success_status', 'completion_status', 'attempt__package__course'
    ]
    search_fields = [
        'objective_id', 'description',
        'attempt__user__username', 'attempt__package__title'
    ]
    readonly_fields = ['attempt']
    
    def attempt_user(self, obj):
        return obj.attempt.user.get_full_name() or obj.attempt.user.username
    attempt_user.short_description = _('User')
    
    def attempt_package(self, obj):
        return obj.attempt.package.title
    attempt_package.short_description = _('Package')
