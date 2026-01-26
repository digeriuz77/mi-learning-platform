from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q
from .models import (
    Scenario, DialogueTree, DialogueNode, PractitionerChoice, 
    MIQuestion, ModuleProgress, UserScore
)


@login_required(login_url='accounts:login')
def game_home(request):
    """Display chapters and challenges"""
    chapters = Chapter.objects.all().prefetch_related('enrollments')
    challenges = Challenge.objects.all()
    
    # Get user's chapter enrollments
    user_enrollments = CourseEnrollment.objects.filter(user=request.user)
    enrolled_chapters = set(e.chapter_id for e in user_enrollments)
    
    # Get user's completed challenges
    completed_challenges = set(
        ChallengeAttempt.objects.filter(user=request.user, is_completed=True).values_list('challenge_id', flat=True)
    )
    
    # Prepare chapter data
    chapter_data = []
    for chapter in chapters:
        enrollment = user_enrollments.filter(chapter=chapter).first()
        chapter_data.append({
            'chapter': chapter,
            'is_enrolled': chapter.id in enrolled_chapters,
            'is_completed': enrollment and enrollment.is_completed if enrollment else False,
            'total_students': chapter.get_total_students(),
            'students_completed': chapter.get_completed_tasks(),
        })
    
    # Prepare challenge data
    challenge_data = []
    for challenge in challenges:
        attempt = ChallengeAttempt.objects.filter(user=request.user, challenge=challenge).first()
        challenge_data.append({
            'challenge': challenge,
            'is_completed': attempt and attempt.is_completed if attempt else False,
            'total_students': challenge.get_total_students(),
            'students_completed': challenge.get_completed_students(),
        })
    
    context = {
        'chapter_data': chapter_data,
        'challenge_data': challenge_data,
        'total_chapters': chapters.count(),
        'total_challenges': challenges.count(),
        'enrolled_chapters': len(enrolled_chapters),
    }
    return render(request, 'game/home.html', context)


@login_required(login_url='accounts:login')
def enroll_chapter(request, chapter_id):
    """Enroll user in a chapter"""
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    enrollment, created = CourseEnrollment.objects.get_or_create(
        user=request.user,
        chapter=chapter
    )
    return redirect('game:chapter_detail', chapter_id=chapter_id)


@login_required(login_url='accounts:login')
def chapter_detail(request, chapter_id):
    """Display chapter with teaching materials and tasks"""
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    
    # Auto-enroll if not already enrolled
    enrollment, created = CourseEnrollment.objects.get_or_create(
        user=request.user,
        chapter=chapter
    )
    
    context = {
        'chapter': chapter,
        'total_students': chapter.get_total_students(),
        'students_completed': chapter.get_completed_tasks(),
        'is_completed': enrollment.is_completed,
        'enrollment': enrollment,
    }
    return render(request, 'game/chapter_detail.html', context)


@login_required(login_url='accounts:login')
def challenge_detail(request, challenge_id):
    """Display challenge with questions"""
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    questions = challenge.questions.all()
    
    # Get or create attempt record
    attempt = ChallengeAttempt.objects.filter(user=request.user, challenge=challenge).first()
    
    # Get question attempts
    question_data = []
    for question in questions:
        q_attempt = QuestionAttempt.objects.filter(
            user=request.user,
            question=question
        ).order_by('-attempted_at').first()
        
        question_data.append({
            'question': question,
            'is_attempted': q_attempt is not None,
            'is_correct': q_attempt.is_correct if q_attempt else False,
        })
    
    correct_count = sum(1 for q in question_data if q['is_correct'])
    
    context = {
        'challenge': challenge,
        'question_data': question_data,
        'total_questions': len(questions),
        'correct_answers': correct_count,
        'progress_percent': (correct_count / len(questions) * 100) if questions else 0,
        'total_students': challenge.get_total_students(),
        'students_completed': challenge.get_completed_students(),
        'is_completed': attempt and attempt.is_completed if attempt else False,
        'attempt': attempt,
    }
    return render(request, 'game/challenge_detail.html', context)


@login_required(login_url='accounts:login')
def quiz_view(request, question_id):
    """Display a specific quiz question"""
    question = get_object_or_404(Question, pk=question_id)
    options = question.options.all()
    
    # Check if already answered correctly
    previous_attempt = QuestionAttempt.objects.filter(
        user=request.user,
        question=question,
        is_correct=True
    ).first()
    
    context = {
        'question': question,
        'options': options,
        'already_completed': previous_attempt is not None,
        'challenge': question.challenge,
    }
    return render(request, 'game/quiz.html', context)


@login_required(login_url='accounts:login')
def check_answer(request, question_id):
    """Check if the selected answer is correct and record the attempt"""
    if request.method == 'POST':
        question = get_object_or_404(Question, pk=question_id)
        selected_option_id = request.POST.get('option')
        
        if not selected_option_id:
            return render(request, 'game/quiz.html', {
                'question': question,
                'options': question.options.all(),
                'error': 'Please select an option'
            })
        
        selected_option = get_object_or_404(Option, pk=selected_option_id)
        is_correct = selected_option.is_correct
        
        points_earned = question.points if is_correct else 0
        
        # Record the attempt
        attempt = QuestionAttempt.objects.create(
            user=request.user,
            question=question,
            selected_option=selected_option,
            is_correct=is_correct,
            points_earned=points_earned
        )
        
        # Update challenge attempt if all questions correct
        if question.challenge:
            all_questions = question.challenge.questions.all()
            correct_answers = QuestionAttempt.objects.filter(
                user=request.user,
                question__challenge=question.challenge,
                is_correct=True
            ).values_list('question_id', flat=True).distinct()
            
            if len(correct_answers) == all_questions.count():
                from django.utils import timezone
                challenge_attempt, created = ChallengeAttempt.objects.get_or_create(
                    user=request.user,
                    challenge=question.challenge
                )
                challenge_attempt.is_completed = True
                challenge_attempt.score = question.challenge.points
                challenge_attempt.completed_at = timezone.now()
                challenge_attempt.save()
        
        # Update user score
        user_score, created = UserScore.objects.get_or_create(user=request.user)
        user_score.update_score()
        
        context = {
            'question': question,
            'selected_option': selected_option,
            'is_correct': is_correct,
            'hint': question.hint if not is_correct else None,
            'points_earned': points_earned,
            'challenge': question.challenge,
        }
        return render(request, 'game/result.html', context)
    
    return render(request, 'game/quiz.html', {'question': get_object_or_404(Question, pk=question_id)})


@login_required(login_url='accounts:login')
def leaderboard(request):
    """Display leaderboard with actual user scores"""
    # Get all users with scores, ordered by points
    user_scores = UserScore.objects.all().order_by('-total_points', '-challenges_completed')
    
    # Add rank to each user
    leaderboard_data = []
    for rank, user_score in enumerate(user_scores, 1):
        user = user_score.user
        leaderboard_data.append({
            'rank': rank,
            'user': user,
            'name': user.first_name or user.username,
            'score': user_score.total_points,
            'challenges_completed': user_score.challenges_completed,
            'chapters_completed': user_score.chapters_completed,
            'is_current_user': user == request.user,
        })
    
    # Get current user's rank
    current_user_rank = next(
        (item['rank'] for item in leaderboard_data if item['is_current_user']),
        None
    )
    
    # Get statistics
    total_students = User.objects.filter(is_staff=False).count()
    total_challenges = Challenge.objects.count()
    total_chapters = Chapter.objects.count()
    
    context = {
        'leaderboard': leaderboard_data,
        'current_user_rank': current_user_rank,
        'total_students': total_students,
        'total_challenges': total_challenges,
        'total_chapters': total_chapters,
    }
    return render(request, 'game/leaderboard.html', context)

