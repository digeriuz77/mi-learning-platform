from django.db import models
from django.contrib.auth.models import User
import json

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


class Scenario(models.Model):
    """Represents an MI learning scenario/dialogue tree"""
    SCENARIO_TYPE_CHOICES = [
        ('scenario', 'Client Scenario'),
        ('assessment', 'Skill Assessment'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    scenario_type = models.CharField(max_length=10, choices=SCENARIO_TYPE_CHOICES, default='scenario')
    module_number = models.IntegerField(help_text="Module number (1-6)")
    difficulty = models.CharField(
        max_length=15, 
        choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')],
        default='beginner'
    )
    order = models.IntegerField(default=0)

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


class DialogueTree(models.Model):
    """Represents a complete MI dialogue tree from JSON modules"""
    title = models.CharField(max_length=200)
    learning_objective = models.TextField()
    technique_focus = models.CharField(max_length=100)
    stage_of_change = models.CharField(max_length=50)
    mi_process = models.CharField(max_length=50)
    description = models.TextField()
    start_node = models.CharField(max_length=20)
    module_number = models.IntegerField(help_text="Module number (1-6)")
    
    def __str__(self):
        return f"Module {self.module_number}: {self.title}"


class DialogueNode(models.Model):
    """Represents individual nodes in MI dialogue tree"""
    tree = models.ForeignKey(DialogueTree, on_delete=models.CASCADE, related_name='nodes')
    node_id = models.CharField(max_length=20)
    patient_statement = models.TextField()
    patient_context = models.TextField()
    change_talk_present = models.BooleanField(default=False)
    change_talk_type = models.CharField(max_length=10, blank=True)  # D, A, R, N, C, T
    is_ending = models.BooleanField(default=False)
    outcome = models.TextField(blank=True)
    learning_summary = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Node {self.node_id} in {self.tree.title}"


class PractitionerChoice(models.Model):
    """Represents practitioner response options in dialogue tree"""
    node = models.ForeignKey(DialogueNode, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    technique = models.CharField(max_length=100)
    next_node_id = models.CharField(max_length=20)
    feedback = models.TextField()
    is_correct_technique = models.BooleanField(default=False)
    is_mistake = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['id']
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"Choice: {self.text[:50]}..."

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Question: {self.story[:30]}..."


class MIQuestion(models.Model):
    """Represents MI skill assessment questions within a scenario"""
    scenario = models.ForeignKey(Scenario, related_name='questions', on_delete=models.CASCADE, null=True, blank=True)
    patient_statement = models.TextField(help_text="Client dialogue or statement")
    client_context = models.TextField(help_text="Client context and emotional state")
    dialogue_prompt = models.TextField(help_text="Dialogue prompt for learner response")
    technique_focus = models.CharField(max_length=50, blank=True)
    hint = models.TextField(help_text="MI technique guidance", blank=True)
    points = models.IntegerField(default=100)
    change_talk_present = models.BooleanField(default=False)
    change_talk_type = models.CharField(max_length=10, blank=True)  # D, A, R, N, C, T
    
    def __str__(self):
        return f"MIQuestion: {self.patient_statement[:30]}..."


class ScenarioEnrollment(models.Model):
    """Tracks which users are enrolled in which scenarios"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scenario_enrollments')
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'scenario')

    def __str__(self):
        return f"{self.user.username} - {self.scenario.title}"


class ScenarioAttempt(models.Model):
    """Tracks user attempts on scenarios"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scenario_attempts')
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='scenario_attempts')
    is_completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0, help_text="Score earned in this attempt")
    completed_at = models.DateTimeField(null=True, blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']
        unique_together = ('user', 'scenario')

    def __str__(self):
        return f"{self.user.username} - {self.scenario.title}"


class MIQuestionAttempt(models.Model):
    """Tracks user attempts on MI questions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mi_question_attempts')
    question = models.ForeignKey(MIQuestion, on_delete=models.CASCADE)
    selected_response = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)
    points_earned = models.IntegerField(default=0)
    attempted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-attempted_at']

    def __str__(self):
        return f"{self.user.username} - MI Question {self.question.id}"


class ModuleProgress(models.Model):
    """Tracks user progress through MI dialogue modules"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_progress')
    scenario = models.ForeignKey(Scenario, on_delete=models.CASCADE, related_name='progress')
    nodes_completed = models.JSONField(default=list, help_text="List of completed node IDs")
    current_node = models.CharField(max_length=20, default='start')
    techniques_demonstrated = models.JSONField(default=list, help_text="List of MI techniques used correctly")
    completion_status = models.CharField(
        max_length=20,
        choices=[
            ('not_started', 'Not Started'),
            ('in_progress', 'In Progress'),
            ('completed_good', 'Completed - Good'),
            ('completed_moderate', 'Completed - Moderate'),
            ('completed_poor', 'Completed - Poor')
        ],
        default='not_started'
    )
    completion_score = models.IntegerField(default=0, help_text="Final engagement score (0-100)")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - Module {self.scenario.module_number}"


class UserScore(models.Model):
    """Tracks total user scores for MI skill mastery"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_score')
    total_points = models.IntegerField(default=0)
    scenarios_completed = models.IntegerField(default=0)
    modules_completed = models.IntegerField(default=0)
    
    # MI-specific skill tracking
    technique_mastery = models.JSONField(default=dict, help_text="Mastery levels for each MI technique")
    change_talk_evoked = models.IntegerField(default=0, help_text="Total change talk successfully evoked")
    reflections_offered = models.IntegerField(default=0, help_text="Total reflections offered")
    summaries_created = models.IntegerField(default=0, help_text="Total summaries created")
    
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.total_points} points"

    def update_score(self):
        """Recalculate score from scenario attempts"""
        scenario_attempts = self.user.scenario_attempts.filter(is_completed=True)
        self.total_points = sum(attempt.score for attempt in scenario_attempts)
        self.scenarios_completed = scenario_attempts.count()
        
        scenario_completions = self.user.scenario_enrollments.filter(is_completed=True)
        self.modules_completed = scenario_completions.count()
        
        self.save()