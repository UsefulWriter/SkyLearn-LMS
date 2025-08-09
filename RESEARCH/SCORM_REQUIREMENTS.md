# SCORM Implementation Requirements for UsefulWriter LMS

## Recommended Approach Based on Current Architecture

### 1. **SCORM Version Support**
**Recommendation**: Support both SCORM 1.2 and SCORM 2004
- SCORM 1.2 for legacy content compatibility
- SCORM 2004 for advanced features and sequencing
- xAPI/Tin Can API for future-proofing

### 2. **Integration Strategy**
**Recommendation**: Hybrid approach - SCORM as a content type alongside existing content
- Create a new `ScormPackage` model linked to `Course`
- Allow courses to have both native content (Upload, UploadVideo) and SCORM packages
- Lecturers can mix content types within a single course

### 3. **Core Features Required**

#### Import & Storage
- Upload SCORM packages as .zip files
- Extract and validate manifest (imsmanifest.xml)
- Store package files in dedicated directory structure
- Package versioning support

#### Launch & Runtime
- iframe-based player for SCORM content
- SCORM API implementation (JavaScript)
- Session management for tracking
- Bookmark/resume capability

#### Tracking & Reporting
- Track these SCORM data elements:
  - cmi.core.lesson_status (passed, completed, failed, incomplete)
  - cmi.core.score.raw (numeric score)
  - cmi.core.total_time (time spent)
  - cmi.interactions.* (detailed interaction tracking)
  - cmi.objectives.* (learning objectives)
- Store attempts with timestamps
- Progress visualization

### 4. **Database Schema Requirements**

```python
# New models needed:

class ScormPackage(models.Model):
    course = ForeignKey(Course)
    title = CharField()
    version = CharField()  # SCORM version (1.2 or 2004)
    package_file = FileField()  # Original .zip
    extracted_path = CharField()  # Where content is extracted
    manifest_data = JSONField()  # Parsed manifest
    entry_point = CharField()  # Launch URL
    
class ScormAttempt(models.Model):
    package = ForeignKey(ScormPackage)
    user = ForeignKey(User)
    started_at = DateTimeField()
    completed_at = DateTimeField(null=True)
    status = CharField()  # passed, completed, failed, incomplete
    score_raw = FloatField(null=True)
    score_min = FloatField(null=True)
    score_max = FloatField(null=True)
    total_time = DurationField()
    suspend_data = TextField()  # For resume
    
class ScormInteraction(models.Model):
    attempt = ForeignKey(ScormAttempt)
    interaction_id = CharField()
    type = CharField()
    timestamp = DateTimeField()
    correct_response = TextField()
    learner_response = TextField()
    result = CharField()
    latency = DurationField()
```

### 5. **Integration with Existing Systems**

#### Grade System Integration
- Map SCORM scores to existing grade scale:
  - 90-100% → A+ (4.0)
  - 85-89% → A (4.0)
  - 80-84% → A- (3.7)
  - etc.
- Create `ScormGrade` model linking to `TakenCourse`
- Weight SCORM activities in final grade calculation

#### Quiz System Compatibility
- SCORM packages can be treated as a special quiz type
- Inherit quiz settings (single_attempt, pass_mark)
- Show in quiz list with SCORM indicator

### 6. **Technical Implementation**

#### Python Dependencies
```python
# requirements/base.txt additions
python-scorm-parser  # For manifest parsing
django-storages  # For scalable file storage
celery  # For async package processing
```

#### JavaScript Components
- SCORM 1.2 API Adapter
- SCORM 2004 API Adapter
- Communication bridge between iframe and Django

#### File Structure
```
scorm/
├── models.py
├── views.py
├── urls.py
├── forms.py
├── admin.py
├── api.py  # SCORM API endpoints
├── parsers.py  # Manifest parsing
├── validators.py  # Package validation
├── static/
│   └── scorm/
│       ├── js/
│       │   ├── scorm12.js
│       │   ├── scorm2004.js
│       │   └── player.js
│       └── css/
│           └── player.css
├── templates/
│   └── scorm/
│       ├── package_list.html
│       ├── package_upload.html
│       ├── player.html
│       └── reports.html
└── tests/
```

### 7. **User Permissions**

- **Students**: Launch and complete SCORM packages
- **Lecturers**: Upload, manage, and view reports for their courses
- **Admins**: Full access plus system-wide reports

### 8. **Additional Considerations**

#### Security
- Validate SCORM packages for malicious content
- Sanitize JavaScript in packages
- Implement CSP headers for iframe content
- Restrict file types in packages

#### Performance
- Async processing for large package uploads
- CDN support for SCORM content delivery
- Database indexing for tracking queries
- Caching for frequently accessed packages

#### Compliance
- Full SCORM RTE compliance testing
- ADL test suite validation
- Accessibility (WCAG 2.1) for player interface

## Next Steps

1. Confirm these requirements match your needs
2. Decide on specific SCORM features priority
3. Choose between building custom or using existing packages
4. Define timeline and milestones
5. Set up development environment for SCORM testing

## Questions Still Needing Answers

1. **Budget/Time**: Build custom vs use commercial SCORM engine?
2. **Scale**: How many concurrent SCORM sessions expected?
3. **Content Source**: Will you create SCORM content or import from vendors?
4. **Mobile Support**: Need mobile app SCORM playback?
5. **Offline Mode**: Support offline SCORM with sync?
6. **LTI Support**: Need Learning Tools Interoperability alongside SCORM?
7. **Reporting Depth**: Basic completion or detailed interaction analytics?
8. **Migration**: Any existing SCORM content to migrate?

## Recommended Python Packages to Evaluate

1. **django-scorm**: Basic SCORM 1.2 support (limited features)
2. **python-scorm-parser**: Parse SCORM manifests
3. **tincan**: Python library for xAPI/Tin Can
4. **Build Custom**: Most flexible but time-intensive

## Estimated Development Effort

- **Basic SCORM 1.2**: 2-3 weeks
- **Full SCORM 1.2 + 2004**: 4-6 weeks
- **Complete with xAPI**: 6-8 weeks
- **Testing & Integration**: 1-2 weeks
- **Documentation**: 1 week

Total: 4-11 weeks depending on feature scope