# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SkyLearn is a Django 5.0 LTS-based Learning Management System for educational institutions with multi-language support (English, French, Spanish, Russian) and comprehensive features for course management, assessments, and grading.

## Essential Commands

### Development Setup
```bash
# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements/local.txt  # For development with Black formatter

# Environment configuration
cp .env.example .env
# Edit .env with your settings (SECRET_KEY, EMAIL_CONFIG, DEBUG=True)

# Database setup
python manage.py migrate
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Common Development Tasks
```bash
# Run tests
python manage.py test
python manage.py test accounts.tests  # Test specific app
python manage.py test accounts.tests.test_decorators.TestDecorators.test_admin_required  # Single test

# Database operations
python manage.py makemigrations
python manage.py migrate
python manage.py dbshell  # Access database shell

# Translation management  
python manage.py makemessages -l fr  # Create French translations
python manage.py compilemessages  # Compile translations

# Code formatting (if Black is installed)
black . --line-length 80 --exclude="venv/|.venv/|migrations/"

# Create fixture data
python manage.py dumpdata course.Course --indent 2 > fixtures/courses.json
python manage.py loaddata fixtures/courses.json
```

## Architecture Overview

### Django Project Structure
- **Project Root**: `config/` (settings.py, urls.py)
- **Main Apps**:
  - `accounts/` - User management with multi-role system (Student, Lecturer, Parent, Department Head)
  - `course/` - Program and course management with multilingual support
  - `quiz/` - Assessment system with multiple question types
  - `result/` - Grading and GPA/CGPA calculation
  - `core/` - Dashboard and news functionality
  - `payments/` - Stripe/GoPay integration

### Key Architectural Patterns

#### Authentication & Authorization
- **Custom User Model**: `accounts.User` extends `AbstractUser`
- **Role-based decorators**: `@admin_required`, `@lecturer_required`, `@student_required`
- **User hierarchy**: User → Student/Lecturer/Parent → Extended profiles

#### Data Flow Architecture
```python
# Academic structure
Program → Course → CourseAllocation → Quiz → Results
Session/Semester → TakenCourse → GPA/CGPA calculation

# User journey
Registration → Role Assignment → Program Enrollment → Course Access → Assessment → Grading
```

#### Model Translation Strategy
All content models use `django-modeltranslation` for multilingual fields:
- Course: `title_en`, `title_fr`, `title_es`, `title_ru`
- Program, Quiz, News follow same pattern

#### Signal-Based Activity Logging
Models automatically log activities via Django signals to `ActivityLog` model for audit trail.

### Critical Integration Points

#### Session & Semester Management
- `Session` model controls academic year
- `Semester` model manages terms
- `is_current_session` and `is_current_semester` flags control active period
- Course registration restricted by current session/semester

#### Grade Calculation System
```python
# TakenCourse model automatically calculates:
total = assignment + mid_exam + quiz + attendance + final_exam
grade = calculate_grade(total)  # A+, A, A-, B+, etc.
point = grade_to_point(grade)   # 4.0 scale
```

#### Quiz System Architecture
- `Quiz` → `Question` (base) → `MCQuestion`/`EssayQuestion`
- `Sitting` model tracks user quiz sessions
- Progress saved automatically for incomplete attempts
- Randomization and single-attempt controls

## Development Considerations

### Database Queries
- Use `select_related()` for ForeignKey relationships
- Use `prefetch_related()` for ManyToMany and reverse ForeignKey
- QuerySets in managers for complex filtering

### Template Inheritance
- All templates extend `templates/base.html`
- Use `{% load i18n %}` for translation support
- Bootstrap 5.3.2 and FontAwesome 6.5.1 available globally

### File Upload Validation
```python
# Allowed file extensions for course materials
["pdf", "docx", "doc", "xls", "xlsx", "ppt", "pptx", "zip", "rar", "7zip"]
```

### Static Files
- Development: Django serves from `/static/`
- Production: WhiteNoise handles static files
- SCSS compiled to CSS in `static/css/`

### Testing Approach
- Test decorators in `accounts/tests/test_decorators.py`
- Use `Factory Boy` for test data generation
- Role-based access testing is critical

## Environment Variables (.env)
```
DEBUG=True
SECRET_KEY=<generate-secure-key>
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend  # Dev
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_FROM_ADDRESS=SkyLearn <email@example.com>
EMAIL_HOST_USER=<email>
EMAIL_HOST_PASSWORD=<password>
```

## Current TODO Items (from TODO.md)
- School calendar implementation
- Payment integration completion
- Dashboard with live data
- Data export for all tables
- PDF report generation with xhtml2pdf

## Production Deployment
```bash
pip install -r requirements/production.txt
# Uses: gunicorn, django-storages[boto3], django-anymail[amazon_ses]
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```