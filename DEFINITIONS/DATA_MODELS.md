# Data Models - UsefulWriter LMS

## Database Schema Design

### Core Principles
- **Database**: PostgreSQL via Supabase
- **Real-time**: Supabase real-time subscriptions for live updates
- **Row Level Security**: Database-level access control
- **Soft Deletes**: Maintain data integrity with deleted_at timestamps
- **Audit Fields**: created_at, updated_at, created_by, updated_by on all tables

## 1. User Management

### users (Supabase Auth Extended)
```sql
-- Extends Supabase auth.users
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    display_name TEXT,
    avatar_url TEXT,
    date_of_birth DATE, -- For age verification (14+)
    timezone TEXT DEFAULT 'America/New_York',
    bio TEXT,
    preferred_language TEXT DEFAULT 'en',
    
    -- Subscription & Access
    subscription_status TEXT DEFAULT 'free', -- free, active, cancelled, past_due
    subscription_tier TEXT, -- basic, premium, lifetime
    subscription_expires_at TIMESTAMPTZ,
    stripe_customer_id TEXT,
    
    -- Learning Preferences
    daily_learning_goal INTEGER DEFAULT 30, -- minutes
    email_notifications JSONB DEFAULT '{
        "course_updates": true,
        "weekly_progress": true,
        "promotional": false,
        "drip_content": true
    }',
    
    -- Analytics
    last_active_at TIMESTAMPTZ,
    total_learning_minutes INTEGER DEFAULT 0,
    courses_completed INTEGER DEFAULT 0,
    current_streak_days INTEGER DEFAULT 0,
    longest_streak_days INTEGER DEFAULT 0,
    
    -- System
    role TEXT DEFAULT 'student', -- student, instructor, admin
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_subscription_status ON profiles(subscription_status);
CREATE INDEX idx_profiles_role ON profiles(role);
```

## 2. Course Management

### courses
```sql
CREATE TABLE courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT UNIQUE NOT NULL, -- URL-friendly identifier
    
    -- Basic Info
    title TEXT NOT NULL,
    subtitle TEXT,
    description TEXT NOT NULL,
    thumbnail_url TEXT,
    preview_video_url TEXT,
    
    -- Instructor
    instructor_id UUID REFERENCES profiles(id),
    instructor_name TEXT NOT NULL, -- Denormalized for performance
    
    -- Categorization
    category TEXT NOT NULL, -- programming, business, design, etc.
    subcategory TEXT,
    tags TEXT[], -- Array of tags for search
    difficulty_level TEXT NOT NULL, -- beginner, intermediate, advanced
    
    -- Pricing & Access
    price_cents INTEGER DEFAULT 0, -- 0 = free
    is_free BOOLEAN GENERATED ALWAYS AS (price_cents = 0) STORED,
    access_type TEXT DEFAULT 'paid', -- free, paid, subscription
    enrollment_count INTEGER DEFAULT 0,
    
    -- Content Details
    total_duration_minutes INTEGER DEFAULT 0,
    lesson_count INTEGER DEFAULT 0,
    has_certificate BOOLEAN DEFAULT true,
    language TEXT DEFAULT 'en',
    captions_available TEXT[], -- ['en', 'es', 'fr']
    
    -- Requirements & Outcomes
    prerequisites TEXT[],
    learning_outcomes TEXT[],
    target_audience TEXT,
    
    -- SEO & Marketing
    meta_description TEXT,
    meta_keywords TEXT[],
    
    -- Status
    status TEXT DEFAULT 'draft', -- draft, published, archived
    published_at TIMESTAMPTZ,
    last_updated_at TIMESTAMPTZ,
    
    -- Metrics
    average_rating DECIMAL(2,1) DEFAULT 0,
    total_reviews INTEGER DEFAULT 0,
    completion_rate DECIMAL(3,2) DEFAULT 0, -- Percentage as decimal
    
    -- System
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ -- Soft delete
);

CREATE INDEX idx_courses_slug ON courses(slug);
CREATE INDEX idx_courses_status ON courses(status);
CREATE INDEX idx_courses_category ON courses(category);
CREATE INDEX idx_courses_instructor ON courses(instructor_id);
CREATE INDEX idx_courses_price ON courses(price_cents);
```

### course_sections
```sql
CREATE TABLE course_sections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    
    title TEXT NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL,
    
    -- Metrics
    total_duration_minutes INTEGER DEFAULT 0,
    lesson_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sections_course ON course_sections(course_id);
CREATE INDEX idx_sections_order ON course_sections(course_id, sort_order);
```

### course_lessons
```sql
CREATE TABLE course_lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    section_id UUID NOT NULL REFERENCES course_sections(id) ON DELETE CASCADE,
    
    -- Basic Info
    title TEXT NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL,
    
    -- Content
    content_type TEXT NOT NULL, -- video, article, quiz, assignment, scorm
    video_url TEXT,
    video_duration_seconds INTEGER,
    article_content TEXT, -- Markdown/HTML content
    
    -- Resources
    downloadable_resources JSONB, -- [{name, url, size, type}]
    
    -- Access Control
    is_preview BOOLEAN DEFAULT false, -- Free preview lesson
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lessons_course ON course_lessons(course_id);
CREATE INDEX idx_lessons_section ON course_lessons(section_id);
CREATE INDEX idx_lessons_order ON course_lessons(section_id, sort_order);
```

## 3. User Progress & Enrollment

### enrollments
```sql
CREATE TABLE enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    
    -- Enrollment Details
    enrolled_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ, -- For time-limited access
    access_type TEXT NOT NULL, -- purchased, subscription, free_grant, promotional
    
    -- Payment Info (if purchased)
    payment_amount_cents INTEGER,
    payment_method TEXT, -- stripe, free, promotional_code
    transaction_id TEXT,
    promotional_code_used TEXT,
    
    -- Progress
    progress_percentage INTEGER DEFAULT 0,
    completed_lessons INTEGER DEFAULT 0,
    total_lessons INTEGER NOT NULL,
    last_accessed_at TIMESTAMPTZ,
    last_lesson_id UUID REFERENCES course_lessons(id),
    
    -- Completion
    is_completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMPTZ,
    certificate_issued BOOLEAN DEFAULT false,
    certificate_id TEXT,
    certificate_url TEXT,
    
    -- Learning Analytics
    total_time_spent_minutes INTEGER DEFAULT 0,
    average_quiz_score DECIMAL(3,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, course_id)
);

CREATE INDEX idx_enrollments_user ON enrollments(user_id);
CREATE INDEX idx_enrollments_course ON enrollments(course_id);
CREATE INDEX idx_enrollments_completed ON enrollments(is_completed);
```

### lesson_progress
```sql
CREATE TABLE lesson_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    lesson_id UUID NOT NULL REFERENCES course_lessons(id) ON DELETE CASCADE,
    enrollment_id UUID NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    
    -- Progress Tracking
    status TEXT DEFAULT 'not_started', -- not_started, in_progress, completed
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Video Progress
    video_position_seconds INTEGER DEFAULT 0,
    video_completed BOOLEAN DEFAULT false,
    
    -- Time Tracking
    time_spent_minutes INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    
    -- User Notes
    user_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, lesson_id)
);

CREATE INDEX idx_lesson_progress_user ON lesson_progress(user_id);
CREATE INDEX idx_lesson_progress_enrollment ON lesson_progress(enrollment_id);
CREATE INDEX idx_lesson_progress_status ON lesson_progress(status);
```

## 4. Assessment System

### quizzes
```sql
CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    lesson_id UUID REFERENCES course_lessons(id) ON DELETE CASCADE,
    
    -- Basic Info
    title TEXT NOT NULL,
    description TEXT,
    instructions TEXT,
    
    -- Configuration
    quiz_type TEXT NOT NULL, -- practice, graded, final_exam
    passing_score INTEGER DEFAULT 70, -- Percentage
    time_limit_minutes INTEGER, -- NULL = no time limit
    max_attempts INTEGER DEFAULT 3, -- NULL = unlimited
    
    -- Question Settings
    randomize_questions BOOLEAN DEFAULT false,
    randomize_answers BOOLEAN DEFAULT true,
    show_correct_answers TEXT DEFAULT 'after_submission', -- immediately, after_submission, never
    
    -- Scoring
    total_points INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_quizzes_course ON quizzes(course_id);
CREATE INDEX idx_quizzes_lesson ON quizzes(lesson_id);
```

### quiz_questions
```sql
CREATE TABLE quiz_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    
    -- Question Content
    question_text TEXT NOT NULL,
    question_type TEXT NOT NULL, -- multiple_choice, true_false, short_answer, code
    explanation TEXT, -- Shown after answering
    hint TEXT,
    
    -- For Multiple Choice
    options JSONB, -- [{id, text, is_correct}]
    
    -- For Code Questions
    code_template TEXT,
    test_cases JSONB, -- [{input, expected_output}]
    programming_language TEXT,
    
    -- Scoring
    points INTEGER DEFAULT 1,
    sort_order INTEGER NOT NULL,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_questions_quiz ON quiz_questions(quiz_id);
CREATE INDEX idx_questions_order ON quiz_questions(quiz_id, sort_order);
```

### quiz_attempts
```sql
CREATE TABLE quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    enrollment_id UUID REFERENCES enrollments(id) ON DELETE CASCADE,
    
    -- Attempt Details
    attempt_number INTEGER NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ,
    time_spent_minutes INTEGER,
    
    -- Scoring
    score DECIMAL(5,2),
    percentage DECIMAL(3,2),
    passed BOOLEAN DEFAULT false,
    
    -- Answers
    answers JSONB, -- [{question_id, answer, is_correct, points_earned}]
    
    -- Status
    status TEXT DEFAULT 'in_progress', -- in_progress, submitted, graded
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_attempts_user ON quiz_attempts(user_id);
CREATE INDEX idx_attempts_quiz ON quiz_attempts(quiz_id);
CREATE INDEX idx_attempts_status ON quiz_attempts(status);
```

## 5. Code Challenges

### code_challenges
```sql
CREATE TABLE code_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID REFERENCES courses(id) ON DELETE CASCADE,
    lesson_id UUID REFERENCES course_lessons(id) ON DELETE CASCADE,
    
    -- Challenge Info
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    difficulty TEXT NOT NULL, -- easy, medium, hard
    category TEXT, -- algorithms, data_structures, web, database
    
    -- Problem Statement
    problem_statement TEXT NOT NULL, -- Markdown
    examples TEXT, -- Input/output examples
    constraints TEXT,
    
    -- Code Setup
    supported_languages TEXT[], -- ['python', 'javascript', 'java']
    starter_code JSONB, -- {python: "def solution():", javascript: "function solution()"}
    solution_code JSONB, -- Hidden from users
    
    -- Testing
    test_cases JSONB NOT NULL, -- [{input, expected_output, is_hidden}]
    time_limit_ms INTEGER DEFAULT 5000,
    memory_limit_mb INTEGER DEFAULT 256,
    
    -- Scoring
    points INTEGER DEFAULT 100,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_challenges_course ON code_challenges(course_id);
CREATE INDEX idx_challenges_difficulty ON code_challenges(difficulty);
```

### code_submissions
```sql
CREATE TABLE code_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    challenge_id UUID NOT NULL REFERENCES code_challenges(id) ON DELETE CASCADE,
    
    -- Submission Details
    language TEXT NOT NULL,
    code TEXT NOT NULL,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Execution Results
    status TEXT NOT NULL, -- pending, running, accepted, wrong_answer, time_limit, runtime_error
    test_results JSONB, -- [{passed, input, expected, actual, execution_time}]
    
    -- Metrics
    execution_time_ms INTEGER,
    memory_used_mb INTEGER,
    passed_tests INTEGER,
    total_tests INTEGER,
    score INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_submissions_user ON code_submissions(user_id);
CREATE INDEX idx_submissions_challenge ON code_submissions(challenge_id);
CREATE INDEX idx_submissions_status ON code_submissions(status);
```

## 6. Payments & Subscriptions

### payment_transactions
```sql
CREATE TABLE payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id),
    
    -- Transaction Details
    type TEXT NOT NULL, -- purchase, subscription, refund
    status TEXT NOT NULL, -- pending, completed, failed, refunded
    amount_cents INTEGER NOT NULL,
    currency TEXT DEFAULT 'USD',
    
    -- What was purchased
    product_type TEXT NOT NULL, -- course, subscription
    product_id UUID, -- course_id or subscription_plan_id
    product_name TEXT NOT NULL,
    
    -- Payment Provider
    provider TEXT NOT NULL, -- stripe, free_grant
    provider_transaction_id TEXT,
    provider_customer_id TEXT,
    payment_method_type TEXT, -- card, paypal
    
    -- Promotional
    promotional_code TEXT,
    discount_amount_cents INTEGER DEFAULT 0,
    
    -- Metadata
    metadata JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_user ON payment_transactions(user_id);
CREATE INDEX idx_transactions_status ON payment_transactions(status);
CREATE INDEX idx_transactions_provider ON payment_transactions(provider_transaction_id);
```

### promotional_codes
```sql
CREATE TABLE promotional_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    
    -- Discount Configuration
    discount_type TEXT NOT NULL, -- percentage, fixed_amount
    discount_value INTEGER NOT NULL, -- Percentage (0-100) or cents
    
    -- Applicability
    applicable_to TEXT NOT NULL, -- all_courses, specific_courses, subscription
    applicable_course_ids UUID[], -- If specific courses
    
    -- Usage Limits
    max_uses INTEGER, -- NULL = unlimited
    uses_count INTEGER DEFAULT 0,
    max_uses_per_user INTEGER DEFAULT 1,
    
    -- Validity Period
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES profiles(id)
);

CREATE INDEX idx_promo_codes_code ON promotional_codes(code);
CREATE INDEX idx_promo_codes_active ON promotional_codes(is_active);
```

## 7. AI Assistant & Support

### ai_conversations
```sql
CREATE TABLE ai_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(id), -- If conversation is course-specific
    lesson_id UUID REFERENCES course_lessons(id), -- If lesson-specific
    
    -- Conversation
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    message_count INTEGER DEFAULT 0,
    
    -- Context
    context_type TEXT, -- general, course_help, lesson_help, technical_support
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    requires_human_review BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_conversations_user ON ai_conversations(user_id);
CREATE INDEX idx_ai_conversations_active ON ai_conversations(is_active);
```

### ai_messages
```sql
CREATE TABLE ai_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES ai_conversations(id) ON DELETE CASCADE,
    
    -- Message Content
    role TEXT NOT NULL, -- user, assistant
    content TEXT NOT NULL,
    
    -- Metadata
    tokens_used INTEGER,
    model_used TEXT,
    response_time_ms INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_messages_conversation ON ai_messages(conversation_id);
CREATE INDEX idx_ai_messages_created ON ai_messages(created_at);
```

## 8. Email Courses

### email_courses
```sql
CREATE TABLE email_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Course Info
    name TEXT NOT NULL,
    description TEXT,
    
    -- Configuration
    delivery_schedule TEXT NOT NULL, -- daily, weekdays, weekly
    delivery_time TIME DEFAULT '09:00',
    total_emails INTEGER NOT NULL,
    
    -- Content
    welcome_email_content TEXT,
    completion_email_content TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### email_course_content
```sql
CREATE TABLE email_course_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email_course_id UUID NOT NULL REFERENCES email_courses(id) ON DELETE CASCADE,
    
    -- Email Content
    day_number INTEGER NOT NULL,
    subject TEXT NOT NULL,
    preview_text TEXT,
    html_content TEXT NOT NULL,
    plain_text_content TEXT,
    
    -- Tracking
    sent_count INTEGER DEFAULT 0,
    open_rate DECIMAL(3,2),
    click_rate DECIMAL(3,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_content_course ON email_course_content(email_course_id);
CREATE INDEX idx_email_content_day ON email_course_content(day_number);
```

### email_course_subscriptions
```sql
CREATE TABLE email_course_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    email_course_id UUID NOT NULL REFERENCES email_courses(id) ON DELETE CASCADE,
    
    -- Subscription Details
    subscribed_at TIMESTAMPTZ DEFAULT NOW(),
    current_day INTEGER DEFAULT 0,
    last_sent_at TIMESTAMPTZ,
    next_send_at TIMESTAMPTZ,
    
    -- Status
    status TEXT DEFAULT 'active', -- active, paused, completed, unsubscribed
    completed_at TIMESTAMPTZ,
    unsubscribed_at TIMESTAMPTZ,
    
    -- Engagement
    emails_opened INTEGER DEFAULT 0,
    links_clicked INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, email_course_id)
);

CREATE INDEX idx_email_subs_user ON email_course_subscriptions(user_id);
CREATE INDEX idx_email_subs_status ON email_course_subscriptions(status);
CREATE INDEX idx_email_subs_next_send ON email_course_subscriptions(next_send_at);
```

## 9. Analytics & Logging

### activity_logs
```sql
CREATE TABLE activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    
    -- Activity Details
    action TEXT NOT NULL, -- login, logout, course_view, lesson_complete, etc.
    entity_type TEXT, -- course, lesson, quiz, etc.
    entity_id UUID,
    
    -- Context
    ip_address INET,
    user_agent TEXT,
    session_id TEXT,
    
    -- Additional Data
    metadata JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_activity_user ON activity_logs(user_id);
CREATE INDEX idx_activity_action ON activity_logs(action);
CREATE INDEX idx_activity_created ON activity_logs(created_at);
```

### learning_analytics
```sql
CREATE TABLE learning_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Daily Metrics
    minutes_learned INTEGER DEFAULT 0,
    lessons_completed INTEGER DEFAULT 0,
    quizzes_taken INTEGER DEFAULT 0,
    quiz_average_score DECIMAL(3,2),
    code_challenges_solved INTEGER DEFAULT 0,
    
    -- Engagement
    login_count INTEGER DEFAULT 0,
    videos_watched INTEGER DEFAULT 0,
    resources_downloaded INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, date)
);

CREATE INDEX idx_analytics_user ON learning_analytics(user_id);
CREATE INDEX idx_analytics_date ON learning_analytics(date);
```

## Database Policies (Row Level Security)

### Key RLS Policies

```sql
-- Users can only view their own profile
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

-- Anyone can view published courses
CREATE POLICY "Public can view published courses" ON courses
    FOR SELECT USING (status = 'published');

-- Only enrolled users can view course content
CREATE POLICY "Enrolled users can view lessons" ON course_lessons
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM enrollments 
            WHERE enrollments.user_id = auth.uid() 
            AND enrollments.course_id = course_lessons.course_id
        )
    );

-- Users can only view their own progress
CREATE POLICY "Users can view own progress" ON lesson_progress
    FOR SELECT USING (user_id = auth.uid());

-- Instructors can manage their own courses
CREATE POLICY "Instructors can manage own courses" ON courses
    FOR ALL USING (instructor_id = auth.uid());
```

## Migration Strategy from Current System

### Data Migration Mapping

1. **Users**: accounts.User → profiles
2. **Courses**: course.Course → courses (remove semester/session dependencies)
3. **Enrollments**: course.TakenCourse → enrollments (simplified)
4. **Quizzes**: quiz.Quiz → quizzes (maintain question structure)
5. **Progress**: Create from quiz.Sitting and result.TakenCourse
6. **Payments**: payments.Invoice → payment_transactions

### Key Transformations

- Remove academic session/semester structure
- Convert grade calculations to completion percentages
- Transform role-based permissions to Supabase RLS policies
- Migrate file uploads to Supabase Storage
- Convert Django signals to Supabase triggers