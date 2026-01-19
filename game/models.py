from django.db import models
from django.contrib.auth.models import User

class Chapter(models.Model):
    """Represents a teaching chapter with learning materials and guided tasks"""
    title = models.CharField(max_length=255)
    description = models.TextField()
    content = models.TextField(help_text="Teaching material and learning content")
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

    def get_total_students(self):
        """Get count of students enrolled in this chapter"""
        return self.enrollments.values('user').distinct().count()

    def get_completed_tasks(self):
        """Get count of students who completed this chapter"""
        return self.enrollments.filter(is_completed=True).count()


class Challenge(models.Model):
    """Represents a coding challenge or quiz"""
    CHALLENGE_TYPE_CHOICES = [
        ('quiz', 'Quiz'),
        ('coding', 'Coding Challenge'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    challenge_type = models.CharField(max_length=10, choices=CHALLENGE_TYPE_CHOICES, default='quiz')
    difficulty = models.CharField(
        max_length=10, 
        choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
        default='medium'
    )
    order = models.IntegerField(default=0)
    points = models.IntegerField(default=100, help_text="Points awarded for completing challenge")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.title} ({self.get_challenge_type_display()})"

    def get_total_students(self):
        """Get count of students who attempted this challenge"""
        return self.challenge_attempts.values('user').distinct().count()

    def get_completed_students(self):
        """Get count of students who completed this challenge"""
        return self.challenge_attempts.filter(is_completed=True).values('user').distinct().count()


class Question(models.Model):
    """Represents a quiz question within a challenge"""
    challenge = models.ForeignKey(Challenge, related_name='questions', on_delete=models.CASCADE, null=True, blank=True)
    story = models.TextField(help_text="The question description")
    code = models.TextField(help_text="Code snippet or context", blank=True)
    hint = models.TextField(help_text="Hint for the question", blank=True)
    order = models.IntegerField(default=0)
    points = models.IntegerField(default=100)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Question: {self.story[:30]}..."


class Option(models.Model):
    question = models.ForeignKey(Question, related_name='options', on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class CourseEnrollment(models.Model):
    """Tracks which users are enrolled in which chapters"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_enrollments')
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'chapter')

    def __str__(self):
        return f"{self.user.username} - {self.chapter.title}"


class ChallengeAttempt(models.Model):
    """Tracks user attempts on challenges"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenge_attempts')
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='challenge_attempts')
    is_completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0, help_text="Score earned in this attempt")
    completed_at = models.DateTimeField(null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']
        unique_together = ('user', 'challenge')

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title}"


class QuestionAttempt(models.Model):
    """Tracks user attempts on individual questions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self):
        return f"{self.user.username} - Question {self.question.id}"


class UserScore(models.Model):
    """Tracks total user scores for leaderboard"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_score')
    total_points = models.IntegerField(default=0)
    challenges_completed = models.IntegerField(default=0)
    chapters_completed = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.total_points} points"

    def update_score(self):
        """Recalculate score from challenge attempts"""
        challenge_attempts = self.user.challenge_attempts.filter(is_completed=True)
        self.total_points = sum(attempt.score for attempt in challenge_attempts)
        self.challenges_completed = challenge_attempts.count()
        
        chapter_completions = self.user.course_enrollments.filter(is_completed=True)
        self.chapters_completed = chapter_completions.count()
        
        self.save()