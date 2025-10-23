"""
Assessment models for MRI Training Platform
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class Question(models.Model):
    """
    Individual question for tests
    """
    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('image', 'Image Identification'),
        ('spatial', 'Spatial Reasoning'),
    ]
    
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='mcq')
    question_text = models.TextField(help_text="The question to be displayed")
    question_image = models.ImageField(upload_to='questions/', blank=True, null=True)
    
    # Answer options (for MCQ)
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    
    correct_answer = models.CharField(
        max_length=1, 
        choices=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
        help_text="The correct answer option"
    )
    
    explanation = models.TextField(blank=True, help_text="Explanation of the correct answer")
    difficulty_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Easy, 5=Hard"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['difficulty_level', 'created_at']
    
    def __str__(self):
        return f"{self.question_type} - {self.question_text[:50]}"


class Test(models.Model):
    """
    Test configuration
    """
    title = models.CharField(max_length=200)
    description = models.TextField()
    time_limit_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Time limit in minutes"
    )
    passing_score = models.IntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage to pass"
    )
    questions = models.ManyToManyField(Question, related_name='tests')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def get_total_questions(self):
        return self.questions.count()


class TestAttempt(models.Model):
    """
    Individual test attempt by a user
    """
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.test.title} - {self.status}"
    
    def is_expired(self):
        """Check if test time has expired"""
        if self.status == 'completed':
            return False
        
        time_limit = timezone.timedelta(minutes=self.test.time_limit_minutes)
        return timezone.now() > (self.started_at + time_limit)
    
    def time_remaining_seconds(self):
        """Get remaining time in seconds"""
        if self.status == 'completed':
            return 0
        
        time_limit = timezone.timedelta(minutes=self.test.time_limit_minutes)
        elapsed = timezone.now() - self.started_at
        remaining = time_limit - elapsed
        
        return max(0, int(remaining.total_seconds()))
    
    def calculate_score(self):
        """Calculate the test score based on answers"""
        total_questions = self.answers.count()
        if total_questions == 0:
            return 0
        
        correct_answers = self.answers.filter(is_correct=True).count()
        score = (correct_answers / total_questions) * 100
        
        self.score = round(score, 2)
        self.passed = score >= self.test.passing_score
        self.save()
        
        return self.score


class Answer(models.Model):
    """
    User's answer to a specific question in a test attempt
    """
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    selected_answer = models.CharField(
        max_length=1,
        choices=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
        null=True,
        blank=True
    )
    is_correct = models.BooleanField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(default=0)
    
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['answered_at']
        unique_together = ['attempt', 'question']
    
    def __str__(self):
        return f"{self.attempt.user.username} - Q{self.question.id} - {self.selected_answer}"
    
    def check_answer(self):
        """Check if the selected answer is correct"""
        if self.selected_answer:
            self.is_correct = (self.selected_answer == self.question.correct_answer)
            self.save()
        return self.is_correct
