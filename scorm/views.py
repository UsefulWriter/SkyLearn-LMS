import json
import os
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.views.generic.base import View

from accounts.decorators import admin_required
from course.models import Course
from .models import ScormPackage, ScormAttempt, ScormInteraction, ScormObjective
from .forms import ScormPackageUploadForm, ScormPackageEditForm, ScormPackageFilterForm


class ScormPackageListView(ListView):
    """List all SCORM packages with filtering"""
    model = ScormPackage
    template_name = 'scorm/package_list.html'
    context_object_name = 'packages'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = ScormPackage.objects.select_related('course', 'uploaded_by')
        
        # Apply filters
        form = ScormPackageFilterForm(self.request.GET, user=self.request.user)
        
        if form.is_valid():
            search = form.cleaned_data.get('search')
            course = form.cleaned_data.get('course')
            status = form.cleaned_data.get('status')
            version = form.cleaned_data.get('version')
            
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) |
                    Q(description__icontains=search) |
                    Q(course__title__icontains=search)
                )
            
            if course:
                queryset = queryset.filter(course=course)
            
            if status:
                queryset = queryset.filter(status=status)
            
            if version:
                queryset = queryset.filter(version=version)
        
        # Filter by user permissions
        user = self.request.user
        if not (user.is_superuser or user.is_staff):
            # Students can only see packages from courses they're enrolled in
            if hasattr(user, 'student'):
                enrolled_courses = Course.objects.filter(
                    takencourse__student=user.student
                ).values_list('id', flat=True)
                queryset = queryset.filter(course_id__in=enrolled_courses)
            else:
                queryset = ScormPackage.objects.none()
        
        return queryset.filter(status='ready').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ScormPackageFilterForm(self.request.GET, user=self.request.user)
        return context


@method_decorator(admin_required, name='dispatch')
class ScormPackageCreateView(CreateView):
    """Create new SCORM package (Admin only)"""
    model = ScormPackage
    form_class = ScormPackageUploadForm
    template_name = 'scorm/package_upload.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        response = super().form_valid(form)
        
        # Extract package after creation
        self.object.extract_package()
        
        if self.object.status == 'ready':
            messages.success(self.request, f'SCORM package "{self.object.title}" uploaded and extracted successfully.')
        else:
            messages.error(self.request, f'Error processing SCORM package: {self.object.error_message}')
        
        return response
    
    def get_success_url(self):
        return reverse('scorm:package_detail', kwargs={'slug': self.object.slug})


class ScormPackageDetailView(DetailView):
    """View SCORM package details"""
    model = ScormPackage
    template_name = 'scorm/package_detail.html'
    context_object_name = 'package'
    
    def get_object(self):
        obj = get_object_or_404(ScormPackage, slug=self.kwargs['slug'])
        
        # Check permissions
        user = self.request.user
        if not user.is_authenticated:
            raise Http404()
        
        # Admin/staff can see all packages
        if user.is_superuser or user.is_staff:
            return obj
        
        # Students can only see packages from enrolled courses
        if hasattr(user, 'student'):
            enrolled_courses = Course.objects.filter(
                takencourse__student=user.student
            ).values_list('id', flat=True)
            if obj.course.id not in enrolled_courses:
                raise Http404()
        else:
            raise Http404()
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user's attempts for this package
        if hasattr(self.request.user, 'student') or hasattr(self.request.user, 'lecturer'):
            user_attempts = ScormAttempt.objects.filter(
                package=self.object,
                user=self.request.user
            ).order_by('-started_at')
            context['user_attempts'] = user_attempts
            context['latest_attempt'] = user_attempts.first()
        
        # Get package statistics (for admin/lecturer)
        if self.request.user.is_superuser or hasattr(self.request.user, 'allocated_lecturer'):
            context['attempt_stats'] = self.object.attempts.aggregate(
                total_attempts=Count('id'),
                completed_attempts=Count('id', filter=Q(lesson_status__in=['completed', 'passed']))
            )
        
        return context


@login_required
def launch_scorm_package(request, slug):
    """Launch SCORM package in player"""
    package = get_object_or_404(ScormPackage, slug=slug, status='ready')
    
    # Check permissions
    user = request.user
    if not (user.is_superuser or user.is_staff):
        if hasattr(user, 'student'):
            enrolled_courses = Course.objects.filter(
                takencourse__student=user.student
            ).values_list('id', flat=True)
            if package.course.id not in enrolled_courses:
                raise Http404()
        else:
            raise Http404()
    
    # Check if multiple attempts are allowed
    existing_attempts = ScormAttempt.objects.filter(
        package=package,
        user=user
    )
    
    if not package.allow_multiple_attempts and existing_attempts.exists():
        latest_attempt = existing_attempts.first()
        if latest_attempt.lesson_status in ['completed', 'passed']:
            messages.warning(request, 'You have already completed this SCORM package and multiple attempts are not allowed.')
            return redirect('scorm:package_detail', slug=slug)
    
    # Get or create current attempt
    current_attempt, created = ScormAttempt.objects.get_or_create(
        package=package,
        user=user,
        lesson_status='not_attempted',
        defaults={
            'started_at': now(),
            'lesson_status': 'incomplete'
        }
    )
    
    if not created:
        current_attempt.last_accessed = now()
        current_attempt.save()
    
    # Get other packages in the same course
    other_packages = ScormPackage.objects.filter(
        course=package.course,
        status='ready'
    ).exclude(id=package.id).order_by('created_at')
    
    # Get completed packages by this user
    completed_packages = ScormAttempt.objects.filter(
        user=user,
        package__course=package.course,
        lesson_status__in=['completed', 'passed']
    ).values_list('package_id', flat=True).distinct()
    
    # Get attempt count for this package
    attempt_count = existing_attempts.count()
    
    # Prepare SCORM launch data
    context = {
        'package': package,
        'attempt': current_attempt,
        'launch_url': f"/media/{package.extracted_path}/{package.entry_point}",
        'scorm_api_url': reverse('scorm:api'),
        'other_packages': other_packages[:5],  # Show max 5 other modules
        'completed_packages': list(completed_packages),
        'attempt_count': attempt_count,
    }
    
    # Use the updated player template with full-screen layout
    return render(request, 'scorm/player.html', context)


@method_decorator(admin_required, name='dispatch')
class ScormPackageUpdateView(UpdateView):
    """Edit SCORM package settings (Admin only)"""
    model = ScormPackage
    form_class = ScormPackageEditForm
    template_name = 'scorm/package_edit.html'
    
    def get_success_url(self):
        messages.success(self.request, f'SCORM package "{self.object.title}" updated successfully.')
        return reverse('scorm:package_detail', kwargs={'slug': self.object.slug})


@method_decorator(admin_required, name='dispatch')
class ScormPackageDeleteView(DeleteView):
    """Delete SCORM package (Admin only)"""
    model = ScormPackage
    template_name = 'scorm/package_confirm_delete.html'
    
    def get_success_url(self):
        messages.success(self.request, f'SCORM package "{self.object.title}" deleted successfully.')
        return reverse('scorm:package_list')
    
    def delete(self, request, *args, **kwargs):
        # Clean up extracted files
        obj = self.get_object()
        if obj.extracted_path:
            extracted_path = Path(obj.package_file.path).parent / obj.slug
            if extracted_path.exists():
                import shutil
                shutil.rmtree(extracted_path, ignore_errors=True)
        
        return super().delete(request, *args, **kwargs)


@csrf_exempt
@login_required
def scorm_api(request):
    """SCORM API endpoint for handling SCORM communication"""
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            method = data.get('method')
            parameters = data.get('parameters', [])
            attempt_id = data.get('attempt_id')
            
            # Get the current attempt
            if not attempt_id:
                return JsonResponse({'error': 'No attempt ID provided'}, status=400)
            
            try:
                attempt = ScormAttempt.objects.get(id=attempt_id, user=request.user)
            except ScormAttempt.DoesNotExist:
                return JsonResponse({'error': 'Invalid attempt'}, status=404)
            
            # Handle different SCORM API methods
            if method == 'LMSGetValue':
                element = parameters[0] if parameters else ''
                value = get_scorm_value(attempt, element)
                return JsonResponse({'success': True, 'value': value})
            
            elif method == 'LMSSetValue':
                element = parameters[0] if len(parameters) > 0 else ''
                value = parameters[1] if len(parameters) > 1 else ''
                success = set_scorm_value(attempt, element, value)
                return JsonResponse({'success': success})
            
            elif method == 'LMSCommit':
                attempt.save()
                return JsonResponse({'success': True})
            
            elif method == 'LMSFinish':
                attempt.completed_at = now()
                attempt.save()
                return JsonResponse({'success': True})
            
            else:
                return JsonResponse({'success': True, 'value': ''})
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def get_scorm_value(attempt, element):
    """Get SCORM data model value"""
    
    # Core elements
    if element == 'cmi.core.lesson_status':
        return attempt.lesson_status
    elif element == 'cmi.core.score.raw':
        return str(attempt.score_raw) if attempt.score_raw is not None else ''
    elif element == 'cmi.core.score.min':
        return str(attempt.score_min)
    elif element == 'cmi.core.score.max':
        return str(attempt.score_max)
    elif element == 'cmi.core.lesson_location':
        return attempt.lesson_location
    elif element == 'cmi.core.credit':
        return attempt.credit
    elif element == 'cmi.core.entry':
        return attempt.entry
    elif element == 'cmi.core.total_time':
        return str(attempt.total_time) if attempt.total_time else '00:00:00'
    elif element == 'cmi.core.session_time':
        return str(attempt.session_time) if attempt.session_time else '00:00:00'
    elif element == 'cmi.core.exit':
        return attempt.exit_mode
    elif element == 'cmi.suspend_data':
        return attempt.suspend_data
    elif element == 'cmi.launch_data':
        return ''  # Not implemented yet
    elif element == 'cmi.comments':
        return ''  # Not implemented yet
    elif element == 'cmi.comments_from_lms':
        return ''  # Not implemented yet
    
    # Student info
    elif element == 'cmi.core.student_id':
        return str(attempt.user.id)
    elif element == 'cmi.core.student_name':
        return attempt.user.get_full_name() or attempt.user.username
    
    # System info
    elif element == 'cmi.core._version':
        return '3.4'
    
    return ''


def set_scorm_value(attempt, element, value):
    """Set SCORM data model value"""
    
    try:
        # Core elements
        if element == 'cmi.core.lesson_status':
            if value in dict(ScormAttempt.STATUS_CHOICES):
                attempt.lesson_status = value
            return True
            
        elif element == 'cmi.core.score.raw':
            try:
                attempt.score_raw = float(value)
            except ValueError:
                return False
            return True
            
        elif element == 'cmi.core.score.min':
            try:
                attempt.score_min = float(value)
            except ValueError:
                return False
            return True
            
        elif element == 'cmi.core.score.max':
            try:
                attempt.score_max = float(value)
            except ValueError:
                return False
            return True
            
        elif element == 'cmi.core.lesson_location':
            attempt.lesson_location = str(value)[:255]
            return True
            
        elif element == 'cmi.core.exit':
            attempt.exit_mode = str(value)[:20]
            return True
            
        elif element == 'cmi.core.session_time':
            # TODO: Parse time format and add to total_time
            return True
            
        elif element == 'cmi.suspend_data':
            attempt.suspend_data = str(value)
            return True
            
        # Interactions (basic implementation)
        elif element.startswith('cmi.interactions.'):
            # TODO: Implement interaction tracking
            return True
            
        # Objectives (basic implementation)
        elif element.startswith('cmi.objectives.'):
            # TODO: Implement objectives tracking
            return True
        
        return True
        
    except Exception:
        return False


@login_required
def user_scorm_progress(request):
    """View user's SCORM progress across all packages"""
    
    attempts = ScormAttempt.objects.filter(user=request.user).select_related(
        'package', 'package__course'
    ).order_by('-started_at')
    
    # Group by package
    progress_by_package = {}
    for attempt in attempts:
        if attempt.package.id not in progress_by_package:
            progress_by_package[attempt.package.id] = {
                'package': attempt.package,
                'latest_attempt': attempt,
                'total_attempts': 0,
                'best_score': 0
            }
        
        progress_by_package[attempt.package.id]['total_attempts'] += 1
        if attempt.score_raw and attempt.score_raw > progress_by_package[attempt.package.id]['best_score']:
            progress_by_package[attempt.package.id]['best_score'] = attempt.score_raw
    
    context = {
        'progress_data': list(progress_by_package.values()),
        'total_packages': len(progress_by_package),
        'completed_packages': len([p for p in progress_by_package.values() 
                                 if p['latest_attempt'].lesson_status in ['completed', 'passed']])
    }
    
    return render(request, 'scorm/user_progress.html', context)
