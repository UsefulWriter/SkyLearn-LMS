# Claude Code Implementation Guide - UsefulWriter LMS

## Project Overview

Create a modern 24/7 online learning platform using Next.js 14+, Tailwind CSS 4, shadcn/ui, FastAPI, and Supabase. This LMS will support individual self-paced learning for teens and adults with flexible monetization options.

## Prerequisites

Before starting implementation, ensure you have:

1. **Node.js 18+** and **npm/yarn** installed
2. **Python 3.11+** and **pip** for FastAPI
3. **Supabase account** (free tier available)
4. **Stripe account** (test mode for development)
5. **OpenAI API key** for AI assistant
6. **Git** for version control

## Phase 1: Project Setup & Foundation

### Step 1.1: Initialize Next.js Project

```bash
# Create new Next.js project with TypeScript
npx create-next-app@latest usefulwriter-lms --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

cd usefulwriter-lms

# Install core dependencies
npm install @supabase/supabase-js @supabase/ssr
npm install @stripe/stripe-js stripe
npm install @tanstack/react-query @tanstack/react-query-devtools
npm install zustand
npm install react-hook-form @hookform/resolvers zod
npm install @radix-ui/react-toast @radix-ui/react-dialog @radix-ui/react-dropdown-menu
npm install @monaco-editor/react
npm install video.js @videojs/themes
npm install date-fns
npm install framer-motion
npm install resend

# Install shadcn/ui
npx shadcn-ui@latest init
npx shadcn-ui@latest add button input label textarea select card badge avatar progress toast dialog dropdown-menu

# Dev dependencies
npm install -D @types/video.js
```

### Step 1.2: Configure Tailwind CSS 4

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

### Step 1.3: Set Up Supabase

```bash
# Install Supabase CLI
npm install -g supabase

# Initialize Supabase in your project
supabase init

# Start local Supabase (requires Docker)
supabase start
```

Create `lib/supabase/client.ts`:
```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

Create `lib/supabase/server.ts`:
```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export function createServerClient() {
  const cookieStore = cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value
        },
      },
    }
  )
}
```

### Step 1.4: Environment Configuration

Create `.env.local`:
```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# OpenAI
OPENAI_API_KEY=sk-...

# App
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Email (Resend)
RESEND_API_KEY=re_...
```

## Phase 2: Database Schema Implementation

### Step 2.1: Create Supabase Migrations

```sql
-- Create migration file: supabase/migrations/001_initial_schema.sql
-- (Copy the complete schema from DATA_MODELS.md)

-- Enable Row Level Security
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE courses ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrollments ENABLE ROW LEVEL SECURITY;
-- ... (enable for all tables)

-- Create policies
CREATE POLICY "Users can view own profile" ON profiles
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Public can view published courses" ON courses
  FOR SELECT USING (status = 'published');

-- ... (add all RLS policies)
```

Apply migrations:
```bash
supabase db reset
```

### Step 2.2: Generate TypeScript Types

```bash
# Generate types from your database
supabase gen types typescript --local > types/database.types.ts
```

## Phase 3: Authentication System

### Step 3.1: Create Auth Components

Create `components/auth/LoginForm.tsx`:
```typescript
'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { createClient } from '@/lib/supabase/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
})

type LoginForm = z.infer<typeof loginSchema>

export function LoginForm() {
  const [isLoading, setIsLoading] = useState(false)
  const supabase = createClient()
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true)
    
    const { error } = await supabase.auth.signInWithPassword({
      email: data.email,
      password: data.password,
    })

    if (error) {
      console.error('Login error:', error)
      // Handle error (show toast, etc.)
    }

    setIsLoading(false)
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Sign In</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              {...register('email')}
              placeholder="Enter your email"
            />
            {errors.email && (
              <p className="text-sm text-red-600">{errors.email.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              {...register('password')}
              placeholder="Enter your password"
            />
            {errors.password && (
              <p className="text-sm text-red-600">{errors.password.message}</p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? 'Signing in...' : 'Sign In'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
```

### Step 3.2: Create Auth Pages

Create `app/(auth)/login/page.tsx`:
```typescript
import { LoginForm } from '@/components/auth/LoginForm'

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <LoginForm />
    </div>
  )
}
```

### Step 3.3: Create Auth Store

Create `stores/authStore.ts`:
```typescript
import { create } from 'zustand'
import { User } from '@supabase/supabase-js'

interface AuthState {
  user: User | null
  loading: boolean
  setUser: (user: User | null) => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  setUser: (user) => set({ user }),
  setLoading: (loading) => set({ loading }),
}))
```

## Phase 4: Course Management System

### Step 4.1: Course Components

Create `components/course/CourseCard.tsx`:
```typescript
import Image from 'next/image'
import Link from 'next/link'
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Clock, Users, Star } from 'lucide-react'

interface Course {
  id: string
  slug: string
  title: string
  subtitle?: string
  thumbnail_url?: string
  instructor_name: string
  price_cents: number
  total_duration_minutes: number
  enrollment_count: number
  average_rating: number
  difficulty_level: 'beginner' | 'intermediate' | 'advanced'
  category: string
}

interface CourseCardProps {
  course: Course
  enrolled?: boolean
}

export function CourseCard({ course, enrolled = false }: CourseCardProps) {
  const formatPrice = (cents: number) => {
    if (cents === 0) return 'Free'
    return `$${(cents / 100).toFixed(2)}`
  }

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}h ${mins}m`
  }

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow">
      <div className="relative aspect-video">
        <Image
          src={course.thumbnail_url || '/placeholder-course.jpg'}
          alt={course.title}
          fill
          className="object-cover"
        />
        <div className="absolute top-2 right-2">
          <Badge variant="secondary">
            {course.difficulty_level}
          </Badge>
        </div>
      </div>

      <CardHeader className="pb-2">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <span>{course.category}</span>
          <div className="flex items-center gap-1">
            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
            <span>{course.average_rating.toFixed(1)}</span>
          </div>
        </div>
        <h3 className="font-semibold line-clamp-2">{course.title}</h3>
        <p className="text-sm text-muted-foreground">by {course.instructor_name}</p>
      </CardHeader>

      <CardContent className="pb-2">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{formatDuration(course.total_duration_minutes)}</span>
          </div>
          <div className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            <span>{course.enrollment_count}</span>
          </div>
        </div>
      </CardContent>

      <CardFooter className="pt-0">
        <div className="flex items-center justify-between w-full">
          <span className="font-semibold text-lg">
            {formatPrice(course.price_cents)}
          </span>
          <Button asChild size="sm">
            <Link href={`/courses/${course.slug}`}>
              {enrolled ? 'Continue Learning' : 'View Course'}
            </Link>
          </Button>
        </div>
      </CardFooter>
    </Card>
  )
}
```

### Step 4.2: Course Pages

Create `app/courses/[slug]/page.tsx`:
```typescript
import { notFound } from 'next/navigation'
import { createServerClient } from '@/lib/supabase/server'
import { CourseHeader } from '@/components/course/CourseHeader'
import { CourseCurriculum } from '@/components/course/CourseCurriculum'
import { CourseEnrollment } from '@/components/course/CourseEnrollment'

interface CoursePageProps {
  params: {
    slug: string
  }
}

export default async function CoursePage({ params }: CoursePageProps) {
  const supabase = createServerClient()

  const { data: course, error } = await supabase
    .from('courses')
    .select(`
      *,
      instructor:profiles!instructor_id(full_name, avatar_url),
      sections:course_sections(
        *,
        lessons:course_lessons(*)
      )
    `)
    .eq('slug', params.slug)
    .eq('status', 'published')
    .single()

  if (error || !course) {
    notFound()
  }

  // Check if user is enrolled
  const { data: enrollment } = await supabase
    .from('enrollments')
    .select('*')
    .eq('course_id', course.id)
    .single()

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <CourseHeader course={course} />
          <CourseCurriculum 
            sections={course.sections} 
            enrolled={!!enrollment}
          />
        </div>
        
        <div className="lg:col-span-1">
          <CourseEnrollment 
            course={course}
            enrolled={!!enrollment}
          />
        </div>
      </div>
    </div>
  )
}
```

## Phase 5: Video Player Implementation

### Step 5.1: Video Player Component

Create `components/video/VideoPlayer.tsx`:
```typescript
'use client'

import { useRef, useEffect, useState } from 'react'
import videojs from 'video.js'
import 'video.js/dist/video-js.css'

interface VideoPlayerProps {
  src: string
  poster?: string
  onProgress?: (currentTime: number, duration: number) => void
  onEnded?: () => void
  startTime?: number
}

export function VideoPlayer({
  src,
  poster,
  onProgress,
  onEnded,
  startTime = 0,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const playerRef = useRef<videojs.Player | null>(null)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    if (!videoRef.current) return

    const player = videojs(videoRef.current, {
      controls: true,
      fluid: true,
      responsive: true,
      playbackRates: [0.5, 1, 1.25, 1.5, 2],
      poster,
      sources: [
        {
          src,
          type: 'video/mp4',
        },
      ],
    })

    playerRef.current = player

    player.ready(() => {
      setIsLoaded(true)
      if (startTime > 0) {
        player.currentTime(startTime)
      }
    })

    player.on('timeupdate', () => {
      const currentTime = player.currentTime() || 0
      const duration = player.duration() || 0
      onProgress?.(currentTime, duration)
    })

    player.on('ended', () => {
      onEnded?.()
    })

    return () => {
      if (playerRef.current) {
        playerRef.current.dispose()
        playerRef.current = null
      }
    }
  }, [src, poster, onProgress, onEnded, startTime])

  return (
    <div className="video-container">
      <video
        ref={videoRef}
        className="video-js vjs-default-skin"
        controls
        preload="auto"
        data-setup="{}"
      />
    </div>
  )
}
```

## Phase 6: Payment Integration

### Step 6.1: Stripe Setup

Create `lib/stripe/client.ts`:
```typescript
import { loadStripe } from '@stripe/stripe-js'

export const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!
)
```

Create `lib/stripe/server.ts`:
```typescript
import Stripe from 'stripe'

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
})
```

### Step 6.2: Checkout Flow

Create `app/api/checkout/route.ts`:
```typescript
import { NextRequest, NextResponse } from 'next/server'
import { stripe } from '@/lib/stripe/server'
import { createServerClient } from '@/lib/supabase/server'

export async function POST(request: NextRequest) {
  try {
    const { courseId, priceId } = await request.json()
    const supabase = createServerClient()

    // Get authenticated user
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get course details
    const { data: course } = await supabase
      .from('courses')
      .select('*')
      .eq('id', courseId)
      .single()

    if (!course) {
      return NextResponse.json({ error: 'Course not found' }, { status: 404 })
    }

    // Create Stripe checkout session
    const session = await stripe.checkout.sessions.create({
      customer_email: user.email,
      payment_method_types: ['card'],
      line_items: [
        {
          price_data: {
            currency: 'usd',
            product_data: {
              name: course.title,
              description: course.subtitle,
              images: course.thumbnail_url ? [course.thumbnail_url] : [],
            },
            unit_amount: course.price_cents,
          },
          quantity: 1,
        },
      ],
      mode: 'payment',
      success_url: `${process.env.NEXT_PUBLIC_APP_URL}/courses/${course.slug}?success=true`,
      cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/courses/${course.slug}`,
      metadata: {
        courseId: course.id,
        userId: user.id,
      },
    })

    return NextResponse.json({ sessionId: session.id })
  } catch (error) {
    console.error('Checkout error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
```

## Phase 7: FastAPI Backend Services

### Step 7.1: Initialize FastAPI Project

```bash
# In a separate directory or subdirectory
mkdir fastapi-services
cd fastapi-services

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn python-multipart
pip install supabase-py openai
pip install celery redis
pip install docker # For code execution sandboxing
```

Create `main.py`:
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from supabase import create_client, Client

app = FastAPI(title="UsefulWriter LMS API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

# Auth dependency
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        user = supabase.auth.get_user(credentials.credentials)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/")
async def root():
    return {"message": "UsefulWriter LMS API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### Step 7.2: Code Execution Service

Create `services/code_runner.py`:
```python
import asyncio
import docker
import json
import tempfile
import os
from typing import Dict, Any, List

class CodeRunner:
    def __init__(self):
        self.docker_client = docker.from_env()
        
    async def execute_python(self, code: str, test_cases: List[Dict]) -> Dict[str, Any]:
        """Execute Python code with test cases in a sandboxed environment"""
        
        # Create temporary file with user code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            test_code = self._generate_test_code(code, test_cases)
            f.write(test_code)
            temp_file = f.name
        
        try:
            # Run code in Docker container
            result = self.docker_client.containers.run(
                "python:3.11-alpine",
                f"python /tmp/user_code.py",
                volumes={temp_file: {'bind': '/tmp/user_code.py', 'mode': 'ro'}},
                mem_limit="256m",
                timeout=5,  # 5 second timeout
                remove=True,
                capture_output=True,
                text=True
            )
            
            # Parse results
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {
                    "status": "runtime_error",
                    "error": result.stderr,
                    "passed_tests": 0,
                    "total_tests": len(test_cases)
                }
                
        except docker.errors.ContainerError as e:
            return {
                "status": "runtime_error", 
                "error": str(e),
                "passed_tests": 0,
                "total_tests": len(test_cases)
            }
        except Exception as e:
            return {
                "status": "system_error",
                "error": str(e),
                "passed_tests": 0,
                "total_tests": len(test_cases)
            }
        finally:
            # Clean up temp file
            os.unlink(temp_file)
    
    def _generate_test_code(self, user_code: str, test_cases: List[Dict]) -> str:
        """Generate test harness code"""
        test_template = f"""
import json
import sys
import time
import traceback

# User's code
{user_code}

# Test cases
test_cases = {json.dumps(test_cases)}

results = []
passed = 0

for i, test_case in enumerate(test_cases):
    try:
        start_time = time.time()
        
        # Execute user function with test input
        if 'input' in test_case:
            actual = solution(test_case['input'])
        else:
            actual = solution()
            
        execution_time = int((time.time() - start_time) * 1000)
        
        # Compare with expected output
        expected = test_case['expected_output']
        test_passed = str(actual).strip() == str(expected).strip()
        
        if test_passed:
            passed += 1
            
        results.append({{
            "passed": test_passed,
            "input": test_case.get('input', ''),
            "expected": expected,
            "actual": str(actual),
            "execution_time_ms": execution_time
        }})
        
    except Exception as e:
        results.append({{
            "passed": False,
            "input": test_case.get('input', ''),
            "expected": test_case['expected_output'],
            "actual": f"Error: {{str(e)}}",
            "execution_time_ms": 0
        }})

# Output results as JSON
output = {{
    "status": "accepted" if passed == len(test_cases) else "wrong_answer",
    "passed_tests": passed,
    "total_tests": len(test_cases),
    "test_results": results
}}

print(json.dumps(output))
"""
        return test_template

# Global instance
code_runner = CodeRunner()
```

## Phase 8: AI Assistant Integration

### Step 8.1: OpenAI Service

Create `services/ai_service.py`:
```python
import openai
from typing import Dict, Any, Optional
import os

class AIService:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
    async def chat_completion(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None
    ) -> Dict[str, Any]:
        """Generate AI response for learning assistance"""
        
        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)
        
        # Build message history
        messages = [{"role": "system", "content": system_prompt}]
        
        if conversation_history:
            messages.extend(conversation_history)
            
        messages.append({"role": "user", "content": message})
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )
            
            return {
                "response": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "model": "gpt-3.5-turbo"
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "response": "I'm sorry, I'm having trouble right now. Please try again later."
            }
    
    def _build_system_prompt(self, context: Optional[Dict[str, Any]]) -> str:
        """Build context-aware system prompt"""
        
        base_prompt = """You are a helpful learning assistant for UsefulWriter LMS. 
        You help students understand course material and answer questions about programming, 
        business, and other topics. Always be encouraging and provide clear explanations."""
        
        if not context:
            return base_prompt
            
        context_prompt = base_prompt
        
        if context.get('course_title'):
            context_prompt += f"\n\nCurrent course: {context['course_title']}"
            
        if context.get('lesson_title'):
            context_prompt += f"\nCurrent lesson: {context['lesson_title']}"
            
        if context.get('lesson_content'):
            context_prompt += f"\nLesson content context: {context['lesson_content'][:500]}"
            
        return context_prompt

# Global instance
ai_service = AIService()
```

## Phase 9: Testing Strategy

### Step 9.1: Frontend Testing

```bash
# Install testing dependencies
npm install -D jest @testing-library/react @testing-library/jest-dom
npm install -D @testing-library/user-event
```

Create `components/__tests__/CourseCard.test.tsx`:
```typescript
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { CourseCard } from '../course/CourseCard'

const mockCourse = {
  id: '1',
  slug: 'test-course',
  title: 'Test Course',
  subtitle: 'Learn testing',
  instructor_name: 'John Doe',
  price_cents: 4999,
  total_duration_minutes: 120,
  enrollment_count: 100,
  average_rating: 4.5,
  difficulty_level: 'beginner' as const,
  category: 'Programming',
}

describe('CourseCard', () => {
  it('renders course information correctly', () => {
    render(<CourseCard course={mockCourse} />)
    
    expect(screen.getByText('Test Course')).toBeInTheDocument()
    expect(screen.getByText('by John Doe')).toBeInTheDocument()
    expect(screen.getByText('$49.99')).toBeInTheDocument()
    expect(screen.getByText('2h 0m')).toBeInTheDocument()
  })

  it('shows "Continue Learning" for enrolled courses', () => {
    render(<CourseCard course={mockCourse} enrolled={true} />)
    
    expect(screen.getByText('Continue Learning')).toBeInTheDocument()
  })
})
```

### Step 9.2: Backend Testing

```bash
# Install testing dependencies
pip install pytest httpx pytest-asyncio
```

Create `test_api.py`:
```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_code_execution():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/code/execute", json={
            "language": "python",
            "code": "def solution(n): return n * 2",
            "test_cases": [
                {"input": 5, "expected_output": "10"},
                {"input": 3, "expected_output": "6"}
            ]
        })
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "accepted"
    assert result["passed_tests"] == 2
```

## Phase 10: Deployment & DevOps

### Step 10.1: Vercel Deployment (Frontend)

Create `vercel.json`:
```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "functions": {
    "app/api/**/*": {
      "maxDuration": 30
    }
  }
}
```

### Step 10.2: Railway/Fly.io Deployment (Backend)

Create `Dockerfile` for FastAPI:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 10.3: CI/CD Pipeline

Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run test
      - run: npm run build

  deploy-frontend:
    needs: test-frontend
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: vercel/action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}

  test-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest

  deploy-backend:
    needs: test-backend
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Railway
        uses: railway/deploy-action@v1
        with:
          railway-token: ${{ secrets.RAILWAY_TOKEN }}
```

## Implementation Timeline

### Week 1-2: Foundation
- [ ] Project setup and configuration
- [ ] Database schema implementation
- [ ] Basic authentication system
- [ ] Course management CRUD

### Week 3-4: Core Features
- [ ] Video player integration
- [ ] Progress tracking system
- [ ] Payment processing (Stripe)
- [ ] Basic quiz functionality

### Week 5-6: Advanced Features
- [ ] Code execution service
- [ ] AI assistant integration
- [ ] Email course system
- [ ] Certificate generation

### Week 7-8: Polish & Testing
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] Security hardening
- [ ] Documentation

### Week 9-10: Mobile App
- [ ] React Native setup
- [ ] Core mobile features
- [ ] Push notifications
- [ ] App store submission

## Success Metrics

### Technical Metrics
- **Page Load Time**: < 3 seconds
- **API Response Time**: < 200ms p95
- **Video Start Time**: < 2 seconds
- **Uptime**: > 99.9%

### User Metrics
- **Course Completion Rate**: > 60%
- **User Retention**: > 70% at 30 days
- **Mobile Usage**: > 40% of traffic

### Business Metrics
- **Conversion Rate**: > 5% free to paid
- **Monthly Recurring Revenue**: $5k+ by month 3
- **Customer Lifetime Value**: > $200

Remember to implement features incrementally, test thoroughly, and gather user feedback early and often. Focus on the MVP features first, then iterate based on user needs and business requirements.