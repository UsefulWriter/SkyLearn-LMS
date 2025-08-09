# API Specifications - UsefulWriter LMS

## API Architecture Overview

The UsefulWriter LMS uses a hybrid API architecture:
- **Supabase**: Direct client access for real-time data, auth, and CRUD operations
- **Next.js API Routes**: Server-side operations, Stripe webhooks, SSR data fetching
- **FastAPI**: Complex computations, code execution, AI services, background tasks

## Authentication

All APIs use Supabase JWT tokens for authentication.

### Headers
```http
Authorization: Bearer {supabase_access_token}
Content-Type: application/json
X-Client-Version: 1.0.0
```

## 1. Supabase Direct Access APIs

### Authentication Endpoints

#### Sign Up
```typescript
// POST auth.signUp
const { data, error } = await supabase.auth.signUp({
  email: 'user@example.com',
  password: 'SecurePassword123!',
  options: {
    data: {
      full_name: 'John Doe',
      date_of_birth: '1995-01-01'
    }
  }
})

// Response
{
  user: {
    id: 'uuid',
    email: 'user@example.com',
    created_at: '2024-01-01T00:00:00Z'
  },
  session: {
    access_token: 'jwt_token',
    refresh_token: 'refresh_token',
    expires_at: 1234567890
  }
}
```

#### Sign In
```typescript
// POST auth.signInWithPassword
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'SecurePassword123!'
})
```

#### Sign Out
```typescript
// POST auth.signOut
const { error } = await supabase.auth.signOut()
```

### Course Management

#### Get Courses
```typescript
// GET from('courses')
const { data, error } = await supabase
  .from('courses')
  .select(`
    *,
    instructor:profiles!instructor_id(full_name, avatar_url),
    sections:course_sections(
      *,
      lessons:course_lessons(*)
    )
  `)
  .eq('status', 'published')
  .order('created_at', { ascending: false })
  .range(0, 19) // Pagination

// Response
[
  {
    id: 'uuid',
    slug: 'intro-to-javascript',
    title: 'Introduction to JavaScript',
    description: '...',
    price_cents: 4999,
    instructor: {
      full_name: 'Jane Smith',
      avatar_url: 'https://...'
    },
    sections: [
      {
        id: 'uuid',
        title: 'Getting Started',
        lessons: [...]
      }
    ]
  }
]
```

#### Get Single Course
```typescript
// GET from('courses').single()
const { data, error } = await supabase
  .from('courses')
  .select('*')
  .eq('slug', 'intro-to-javascript')
  .single()
```

### Enrollment Operations

#### Create Enrollment
```typescript
// INSERT into('enrollments')
const { data, error } = await supabase
  .from('enrollments')
  .insert({
    user_id: userId,
    course_id: courseId,
    access_type: 'purchased',
    payment_amount_cents: 4999,
    total_lessons: 25
  })
  .select()
  .single()
```

#### Get User Enrollments
```typescript
// GET from('enrollments')
const { data, error } = await supabase
  .from('enrollments')
  .select(`
    *,
    course:courses(*)
  `)
  .eq('user_id', userId)
  .order('enrolled_at', { ascending: false })
```

### Progress Tracking

#### Update Lesson Progress
```typescript
// UPSERT into('lesson_progress')
const { data, error } = await supabase
  .from('lesson_progress')
  .upsert({
    user_id: userId,
    lesson_id: lessonId,
    course_id: courseId,
    enrollment_id: enrollmentId,
    status: 'completed',
    completed_at: new Date().toISOString(),
    video_position_seconds: 0,
    video_completed: true
  })
  .select()
  .single()
```

### Real-time Subscriptions

#### Subscribe to Progress Updates
```typescript
// SUBSCRIBE to table changes
const channel = supabase
  .channel('progress-updates')
  .on(
    'postgres_changes',
    {
      event: '*',
      schema: 'public',
      table: 'lesson_progress',
      filter: `user_id=eq.${userId}`
    },
    (payload) => {
      console.log('Progress updated:', payload)
    }
  )
  .subscribe()
```

## 2. Next.js API Routes

### Base URL
```
Production: https://usefulwriter.com/api
Development: http://localhost:3000/api
```

### Course Enrollment

#### POST /api/courses/[slug]/enroll
Enroll user in a course (handles payment if required)

```typescript
// Request
POST /api/courses/intro-to-javascript/enroll
{
  "access_type": "purchase",
  "payment_method_id": "pm_1234567890", // Stripe payment method
  "promotional_code": "SAVE20"
}

// Response
{
  "enrollment": {
    "id": "uuid",
    "course_id": "uuid",
    "user_id": "uuid",
    "enrolled_at": "2024-01-01T00:00:00Z",
    "access_type": "purchase"
  },
  "payment": {
    "amount_cents": 3999,
    "currency": "usd",
    "status": "succeeded"
  }
}
```

### Stripe Webhooks

#### POST /api/webhooks/stripe
Handle Stripe webhook events

```typescript
// Headers required
{
  "stripe-signature": "whsec_signature"
}

// Event types handled
- checkout.session.completed
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted
- invoice.payment_succeeded
- invoice.payment_failed
```

### Certificate Generation

#### GET /api/certificates/[enrollmentId]
Generate course completion certificate

```typescript
// Request
GET /api/certificates/abc123

// Response
{
  "certificate_url": "https://storage.usefulwriter.com/certificates/cert_123.pdf",
  "certificate_id": "CERT-2024-001234",
  "issued_at": "2024-01-01T00:00:00Z"
}
```

### User Analytics

#### GET /api/analytics/learning
Get user's learning analytics

```typescript
// Request
GET /api/analytics/learning?period=week

// Response
{
  "total_minutes": 450,
  "lessons_completed": 12,
  "current_streak": 5,
  "courses_in_progress": 3,
  "daily_breakdown": [
    {
      "date": "2024-01-01",
      "minutes": 65,
      "lessons": 2
    }
  ]
}
```

## 3. FastAPI Services

### Base URL
```
Production: https://api.usefulwriter.com
Development: http://localhost:8000
```

### Code Execution Service

#### POST /api/v1/code/execute
Execute code in sandboxed environment

```python
# Request
POST /api/v1/code/execute
{
  "challenge_id": "uuid",
  "language": "python",
  "code": "def solution(n):\n    return n * 2",
  "test_cases": [
    {"input": "5", "expected_output": "10"},
    {"input": "3", "expected_output": "6"}
  ]
}

# Response
{
  "status": "accepted",
  "passed_tests": 2,
  "total_tests": 2,
  "execution_time_ms": 24,
  "memory_used_mb": 12,
  "test_results": [
    {
      "passed": true,
      "input": "5",
      "expected": "10",
      "actual": "10",
      "execution_time_ms": 12
    },
    {
      "passed": true,
      "input": "3",
      "expected": "6",
      "actual": "6",
      "execution_time_ms": 11
    }
  ]
}

# Error Response
{
  "status": "runtime_error",
  "error": "NameError: name 'x' is not defined",
  "line": 3,
  "passed_tests": 0,
  "total_tests": 2
}
```

### AI Assistant Service

#### POST /api/v1/ai/chat
Chat with AI learning assistant

```python
# Request
POST /api/v1/ai/chat
{
  "message": "How do I implement a binary search in Python?",
  "context": {
    "course_id": "uuid",
    "lesson_id": "uuid",
    "conversation_id": "uuid"  # Optional, for continuing conversation
  }
}

# Response
{
  "response": "To implement binary search in Python, you need a sorted array...",
  "conversation_id": "uuid",
  "tokens_used": 245,
  "suggestions": [
    "Would you like to see a complete example?",
    "Should I explain the time complexity?"
  ]
}
```

### Video Processing Service

#### POST /api/v1/videos/upload
Upload and process video content

```python
# Request (multipart/form-data)
POST /api/v1/videos/upload
{
  "file": <video_file>,
  "course_id": "uuid",
  "lesson_id": "uuid",
  "title": "Introduction to Variables"
}

# Response
{
  "job_id": "job_123",
  "status": "processing",
  "estimated_time_seconds": 180
}
```

#### GET /api/v1/videos/status/[job_id]
Check video processing status

```python
# Request
GET /api/v1/videos/status/job_123

# Response
{
  "job_id": "job_123",
  "status": "completed",
  "video_urls": {
    "1080p": "https://cdn.usefulwriter.com/videos/1080p/video.mp4",
    "720p": "https://cdn.usefulwriter.com/videos/720p/video.mp4",
    "480p": "https://cdn.usefulwriter.com/videos/480p/video.mp4"
  },
  "thumbnail_url": "https://cdn.usefulwriter.com/thumbnails/thumb.jpg",
  "duration_seconds": 625
}
```

### Quiz Grading Service

#### POST /api/v1/quiz/submit
Submit quiz for automated grading

```python
# Request
POST /api/v1/quiz/submit
{
  "quiz_id": "uuid",
  "attempt_id": "uuid",
  "answers": [
    {
      "question_id": "q1",
      "answer": "option_a"
    },
    {
      "question_id": "q2",
      "answer": "true"
    },
    {
      "question_id": "q3",
      "answer": "The answer is..."
    }
  ],
  "time_spent_seconds": 480
}

# Response
{
  "score": 85,
  "passed": true,
  "correct_answers": 17,
  "total_questions": 20,
  "breakdown": [
    {
      "question_id": "q1",
      "correct": true,
      "points_earned": 5
    },
    {
      "question_id": "q2",
      "correct": false,
      "points_earned": 0,
      "correct_answer": "false",
      "explanation": "This is false because..."
    }
  ]
}
```

### Email Course Service

#### POST /api/v1/email/subscribe
Subscribe to email course

```python
# Request
POST /api/v1/email/subscribe
{
  "email_course_id": "uuid",
  "user_id": "uuid",
  "delivery_schedule": "daily",
  "delivery_time": "09:00"
}

# Response
{
  "subscription_id": "uuid",
  "status": "active",
  "next_email_at": "2024-01-02T09:00:00Z",
  "total_emails": 30
}
```

#### POST /api/v1/email/send-batch
Send scheduled email course content (internal use)

```python
# Request
POST /api/v1/email/send-batch
{
  "dry_run": false
}

# Response
{
  "emails_sent": 145,
  "failed": 2,
  "next_batch_at": "2024-01-02T09:00:00Z"
}
```

## 4. Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Course not found",
    "details": {
      "course_slug": "non-existent-course"
    }
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "req_abc123"
}
```

### Error Codes
```
AUTH_REQUIRED         - 401 - Authentication required
AUTH_INVALID         - 401 - Invalid credentials
AUTH_EXPIRED         - 401 - Token expired
PERMISSION_DENIED    - 403 - Insufficient permissions
RESOURCE_NOT_FOUND   - 404 - Resource not found
VALIDATION_ERROR     - 400 - Invalid input data
RATE_LIMIT_EXCEEDED  - 429 - Too many requests
PAYMENT_REQUIRED     - 402 - Payment required
PAYMENT_FAILED       - 400 - Payment processing failed
SERVER_ERROR         - 500 - Internal server error
SERVICE_UNAVAILABLE  - 503 - Service temporarily unavailable
```

## 5. Rate Limiting

### Limits by Endpoint Type
```
Authentication:     5 requests/minute
Course Browsing:    60 requests/minute
Content Access:     30 requests/minute
Code Execution:     10 requests/minute
AI Assistant:       20 requests/minute
Video Upload:       5 requests/hour
```

### Rate Limit Headers
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
```

## 6. Pagination

### Standard Pagination Parameters
```typescript
// Request
GET /api/courses?page=2&limit=20&sort=created_at&order=desc

// Response
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 20,
    "total": 145,
    "total_pages": 8,
    "has_next": true,
    "has_prev": true
  }
}
```

## 7. Webhooks (Outgoing)

### Course Completion Webhook
```json
POST {customer_webhook_url}
{
  "event": "course.completed",
  "data": {
    "user_id": "uuid",
    "course_id": "uuid",
    "completed_at": "2024-01-01T00:00:00Z",
    "certificate_url": "https://...",
    "final_score": 92
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "signature": "hmac_sha256_signature"
}
```

## 8. GraphQL Alternative (Future)

For complex queries, consider implementing GraphQL endpoint:

```graphql
query GetCourseWithProgress($courseId: ID!) {
  course(id: $courseId) {
    id
    title
    sections {
      id
      title
      lessons {
        id
        title
        progress {
          status
          completedAt
          timeSpent
        }
      }
    }
    enrollment {
      progressPercentage
      lastAccessedAt
    }
  }
}
```

## 9. API Versioning

- Current version: v1
- Version in URL path: `/api/v1/...`
- Deprecation notice: 6 months minimum
- Sunset period: 3 months after deprecation

## 10. SDK Examples

### TypeScript SDK
```typescript
import { UsefulWriterClient } from '@usefulwriter/sdk';

const client = new UsefulWriterClient({
  apiKey: process.env.USEFULWRITER_API_KEY,
});

// Get courses
const courses = await client.courses.list({
  category: 'programming',
  limit: 10
});

// Enroll in course
const enrollment = await client.enrollments.create({
  courseId: 'uuid',
  paymentMethodId: 'pm_123'
});

// Submit quiz
const result = await client.quiz.submit({
  quizId: 'uuid',
  answers: [...]
});
```

### Python SDK
```python
from usefulwriter import Client

client = Client(api_key=os.getenv("USEFULWRITER_API_KEY"))

# Execute code
result = client.code.execute(
    challenge_id="uuid",
    language="python",
    code="def solution(n): return n * 2"
)

# Chat with AI
response = client.ai.chat(
    message="Explain recursion",
    context={"course_id": "uuid"}
)
```