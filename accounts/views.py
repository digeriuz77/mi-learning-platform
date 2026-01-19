from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import ContactForm

# Landing page (HOME)
def landing_view(request):
    return render(request, "accounts/landing.html")

def home(request):
    return render(request, "accounts/landing.html")

# Signup / Register
def register_view(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('accounts:signup')

        if User.objects.filter(username=email).exists():
            messages.error(request, "Email already exists")
            return redirect('accounts:signup')

        user = User.objects.create_user(
            username=email,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )
        user.save()
        messages.success(request, "Account created successfully")
        return redirect('accounts:login')

    return render(request, "accounts/register.html")

# Login
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect('accounts:dashboard')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('accounts:login')

    return render(request, "accounts/login.html")

# Dashboard (requires login)
@login_required(login_url='accounts:login')
def dashboard_view(request):
    from game.models import CourseEnrollment, QuestionAttempt, UserScore, ChallengeAttempt, Challenge
    
    # Get user's chapter enrollments and progress
    enrollments = CourseEnrollment.objects.filter(user=request.user).select_related('chapter')
    
    chapter_data = []
    total_chapters_completed = 0
    total_chapters = enrollments.count()
    
    for enrollment in enrollments:
        completed = QuestionAttempt.objects.filter(
            user=request.user,
            question__challenge__isnull=False,
            is_correct=True
        ).count()
        total = enrollment.chapter.questions.count() if hasattr(enrollment.chapter, 'questions') else 0
        
        if enrollment.is_completed:
            total_chapters_completed += 1
        
        progress = (completed / total * 100) if total > 0 else 0
        
        chapter_data.append({
            'enrollment': enrollment,
            'completed': completed,
            'total': total,
            'progress': progress,
            'is_completed': enrollment.is_completed,
        })
    
    # Get user's challenge attempts and progress
    all_challenges = Challenge.objects.all()
    challenge_data = []
    total_challenges_completed = 0
    total_challenges = all_challenges.count()
    
    for challenge in all_challenges:
        # Check if user has completed this challenge
        attempt = ChallengeAttempt.objects.filter(user=request.user, challenge=challenge, is_completed=True).first()
        is_completed = attempt is not None
        
        if is_completed:
            total_challenges_completed += 1
        
        # Count correct questions in this challenge
        correct_count = QuestionAttempt.objects.filter(
            user=request.user,
            question__challenge=challenge,
            is_correct=True
        ).count()
        total_questions = challenge.questions.count()
        progress = (correct_count / total_questions * 100) if total_questions > 0 else 0
        
        challenge_data.append({
            'challenge': challenge,
            'correct': correct_count,
            'total': total_questions,
            'progress': progress,
            'is_completed': is_completed,
            'score': attempt.score if attempt else 0,
        })
    
    # Get user score
    user_score = UserScore.objects.filter(user=request.user).first()
    total_points = user_score.total_points if user_score else 0
    
    # Calculate overall progress
    total_items = total_chapters + total_challenges
    completed_items = total_chapters_completed + total_challenges_completed
    overall_progress = (completed_items / total_items * 100) if total_items > 0 else 0
    
    context = {
        "user": request.user,
        "chapter_data": chapter_data,
        "challenge_data": challenge_data,
        "total_score": total_points,
        "overall_progress": overall_progress,
        "chapters_completed": total_chapters_completed,
        "total_chapters": total_chapters,
        "challenges_completed": total_challenges_completed,
        "total_challenges": total_challenges,
    }
    return render(request, "accounts/dashboard.html", context)

# Logout
def logout_view(request):
    logout(request)
    return redirect('accounts:landing')

# Contact form view
def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your message has been sent successfully!")
            return redirect('accounts:contact')
    else:
        form = ContactForm()
    return render(request, "accounts/contact.html", {"form": form})
