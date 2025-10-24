"""
Enhanced Assessment Models for MRI Training Platform
Includes: Categories, Topics, Cohorts, Proctoring, Plagiarism Detection
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg, Count, Q
import json
from datetime import timedelta


class TestCategory(models.Model):
    """
    Test categories for multi-stage pre-screening
    (Cognitive Ability, Detail Orientation, Trainability, Final Validation)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    stage_number = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        help_text="1=Stage 1, 2=Stage 2, 3=Stage 3, 4=Stage 4"
    )
    passing_score = models.IntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage to pass this stage"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['stage_number']
        verbose_name_plural = 'Test Categories'
    
    def __str__(self):
        return f"Stage {self.stage_number}: {self.name}"


class QuestionTopic(models.Model):
    """
    Topics within each test category
    (e.g., Verbal Reasoning, Spatial Reasoning under Cognitive Ability)
    """
    category = models.ForeignKey(TestCategory, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    questions_per_test = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text="Number of random questions from this topic per test"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'name']
        unique_together = ['category', 'name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"
    
    def get_random_questions(self, count=None):
        """Get random active questions from this topic"""
        if count is None:
            count = self.questions_per_test
        return self.questions.filter(is_active=True).order_by('?')[:count]


class Question(models.Model):
    """
    Individual question for tests
    """
    QUESTION_TYPES = [
        ('mcq', 'Multiple Choice'),
        ('image', 'Image Identification'),
        ('spatial', 'Spatial Reasoning'),
        ('dicom', 'DICOM Hotspot'),
        ('annotation', 'Annotation Upload'),
        ('pattern', 'Pattern Recognition'),
        ('error_detection', 'Error Detection'),
        ('verbal', 'Verbal Reasoning'),
        ('numerical', 'Numerical Reasoning'),
    ]
    
    topic = models.ForeignKey(QuestionTopic, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='mcq')
    question_text = models.TextField(help_text="The question to be displayed")
    question_image = models.ImageField(upload_to='questions/', blank=True, null=True)
    
    # For DICOM questions
    dicom_file = models.FileField(upload_to='dicom/', blank=True, null=True)
    hotspot_coordinates = models.JSONField(
        blank=True, 
        null=True,
        help_text="JSON array of correct hotspot regions [{x, y, width, height, label}]"
    )
    
    # For annotation questions
    ground_truth_file = models.FileField(
        upload_to='segmentations/', 
        blank=True, 
        null=True,
        help_text="Ground truth segmentation for comparison"
    )
    dice_threshold = models.FloatField(
        default=0.80,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text="Minimum Dice coefficient to pass annotation"
    )
    
    # Answer options (for MCQ)
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    
    correct_answer = models.CharField(
        max_length=1, 
        choices=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
        blank=True,
        help_text="The correct answer option"
    )
    
    explanation = models.TextField(blank=True, help_text="Explanation of the correct answer")
    difficulty_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1=Easy, 5=Hard"
    )
    
    # Time limit per question (in seconds)
    time_limit_seconds = models.IntegerField(
        default=60,
        validators=[MinValueValidator(10)],
        help_text="Time limit for this question in seconds"
    )
    
    # Scoring weight
    points = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Points awarded for correct answer"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['topic', 'difficulty_level', 'created_at']
        indexes = [
            models.Index(fields=['topic', 'is_active']),
            models.Index(fields=['question_type']),
        ]
    
    def __str__(self):
        return f"{self.topic.name} - {self.question_type} - {self.question_text[:50]}"


class Cohort(models.Model):
    """
    Candidate groups with assigned test categories
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    enabled_categories = models.ManyToManyField(
        TestCategory, 
        related_name='cohorts',
        help_text="Test categories available for this cohort"
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return self.name
    
    def is_test_available(self, category):
        """Check if a test category is available for this cohort"""
        return self.enabled_categories.filter(id=category.id).exists()


class CohortMembership(models.Model):
    """
    Associates users with cohorts
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cohort_memberships')
    cohort = models.ForeignKey(Cohort, on_delete=models.CASCADE, related_name='members')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'cohort']
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.cohort.name}"


class Test(models.Model):
    """
    Test configuration - now linked to category/topics
    """
    category = models.ForeignKey(TestCategory, on_delete=models.CASCADE, related_name='tests')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Time limits
    time_limit_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Overall time limit in minutes"
    )
    
    # Auto-generation settings
    auto_generate_from_topics = models.BooleanField(
        default=True,
        help_text="Automatically generate random questions from category topics"
    )
    
    # Or manual question selection
    manual_questions = models.ManyToManyField(
        Question, 
        related_name='manual_tests',
        blank=True,
        help_text="Manually selected questions (ignored if auto_generate is True)"
    )
    
    passing_score = models.IntegerField(
        default=70,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Minimum percentage to pass (overrides category default if set)"
    )
    
    # Proctoring settings
    require_webcam = models.BooleanField(default=True)
    require_fullscreen = models.BooleanField(default=True)
    snapshot_interval_seconds = models.IntegerField(
        default=180,  # 3 minutes
        validators=[MinValueValidator(120), MaxValueValidator(300)],
        help_text="Interval between webcam/screen snapshots (120-300 seconds)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.category.name} - {self.title}"
    
    def get_total_questions(self):
        """Get total number of questions in this test"""
        if self.auto_generate_from_topics:
            return sum(topic.questions_per_test for topic in self.category.topics.all())
        return self.manual_questions.count()
    
    def generate_question_set(self):
        """Generate a randomized question set from topics"""
        questions = []
        for topic in self.category.topics.all():
            topic_questions = topic.get_random_questions()
            questions.extend(topic_questions)
        return questions


class TestAttempt(models.Model):
    """
    Individual test attempt by a user
    """
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
        ('flagged', 'Flagged for Review'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    cohort = models.ForeignKey(Cohort, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    
    # Proctoring data
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    consent_given = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(null=True, blank=True)
    
    # Plagiarism detection
    similarity_score = models.FloatField(
        null=True, 
        blank=True,
        help_text="Percentage similarity with other attempts"
    )
    flagged_for_plagiarism = models.BooleanField(default=False)
    
    # Generated question set (JSON of question IDs)
    question_set = models.JSONField(
        null=True,
        blank=True,
        help_text="List of question IDs for this attempt"
    )
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'test']),
            models.Index(fields=['status']),
            models.Index(fields=['flagged_for_plagiarism']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.test.title} - {self.status}"
    
    def is_expired(self):
        """Check if test time has expired"""
        if self.status == 'completed':
            return False
        
        time_limit = timedelta(minutes=self.test.time_limit_minutes)
        return timezone.now() > (self.started_at + time_limit)
    
    def time_remaining_seconds(self):
        """Get remaining time in seconds"""
        if self.status == 'completed':
            return 0
        
        time_limit = timedelta(minutes=self.test.time_limit_minutes)
        elapsed = timezone.now() - self.started_at
        remaining = time_limit - elapsed
        
        return max(0, int(remaining.total_seconds()))
    
    def calculate_score(self):
        """Calculate the test score based on answers"""
        total_points = 0
        earned_points = 0
        
        for answer in self.answers.select_related('question').all():
            total_points += answer.question.points
            if answer.is_correct:
                earned_points += answer.question.points
        
        if total_points == 0:
            self.score = 0
        else:
            self.score = round((earned_points / total_points) * 100, 2)
        
        # Determine pass/fail
        passing_threshold = self.test.passing_score
        self.passed = self.score >= passing_threshold
        
        self.save()
        return self.score
    
    def get_skill_gaps(self):
        """Identify topics where user performed poorly"""
        from django.db.models import Avg
        
        topic_performance = []
        for topic in self.test.category.topics.all():
            topic_answers = self.answers.filter(question__topic=topic)
            if topic_answers.exists():
                correct_count = topic_answers.filter(is_correct=True).count()
                total_count = topic_answers.count()
                percentage = (correct_count / total_count) * 100 if total_count > 0 else 0
                
                topic_performance.append({
                    'topic': topic.name,
                    'percentage': round(percentage, 2),
                    'correct': correct_count,
                    'total': total_count,
                    'is_gap': percentage < 60  # Below 60% is a gap
                })
        
        return topic_performance


class Answer(models.Model):
    """
    User's answer to a specific question in a test attempt
    """
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    # For MCQ answers
    selected_answer = models.CharField(
        max_length=1,
        choices=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
        null=True,
        blank=True
    )
    
    # For DICOM hotspot answers
    clicked_coordinates = models.JSONField(
        null=True,
        blank=True,
        help_text="User's clicked coordinates {x, y}"
    )
    
    # For annotation upload answers
    uploaded_segmentation = models.FileField(
        upload_to='user_segmentations/',
        blank=True,
        null=True
    )
    dice_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Dice coefficient for segmentation comparison"
    )
    
    is_correct = models.BooleanField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(default=0)
    
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['answered_at']
        unique_together = ['attempt', 'question']
        indexes = [
            models.Index(fields=['attempt', 'is_correct']),
        ]
    
    def __str__(self):
        return f"{self.attempt.user.username} - Q{self.question.id} - {self.selected_answer}"
    
    def check_answer(self):
        """Check if the selected answer is correct"""
        if self.question.question_type in ['mcq', 'image', 'spatial', 'verbal', 'numerical', 'pattern', 'error_detection']:
            if self.selected_answer:
                self.is_correct = (self.selected_answer == self.question.correct_answer)
            else:
                self.is_correct = False
            self.save()
            
        elif self.question.question_type == 'dicom':
            # Check if clicked coordinates are within hotspot regions
            if self.clicked_coordinates and self.question.hotspot_coordinates:
                self.is_correct = self._check_hotspot_click()
            else:
                self.is_correct = False
            self.save()
            
        elif self.question.question_type == 'annotation':
            # Dice coefficient calculated separately via command
            self.is_correct = self.dice_score >= self.question.dice_threshold if self.dice_score else False
            self.save()
        else:
            self.is_correct = False
            self.save()
        
        return self.is_correct
    
    def _check_hotspot_click(self):
        """Check if click is within any correct hotspot region"""
        click_x = self.clicked_coordinates.get('x')
        click_y = self.clicked_coordinates.get('y')
        
        for region in self.question.hotspot_coordinates:
            x, y, w, h = region['x'], region['y'], region['width'], region['height']
            if x <= click_x <= x + w and y <= click_y <= y + h:
                return True
        return False


class ProctoringEvent(models.Model):
    """
    Stores proctoring snapshots and events during test
    """
    EVENT_TYPES = [
        ('webcam', 'Webcam Snapshot'),
        ('screen', 'Screen Snapshot'),
        ('tab_switch', 'Tab Switch Detected'),
        ('fullscreen_exit', 'Fullscreen Exit'),
        ('copy_paste', 'Copy/Paste Attempt'),
        ('right_click', 'Right Click Attempt'),
    ]
    
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='proctoring_events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    
    # Snapshots
    image_file = models.ImageField(
        upload_to='proctoring/%Y/%m/%d/', 
        blank=True, 
        null=True,
        help_text="Compressed snapshot image"
    )
    
    # Event metadata
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Additional event data (browser info, mouse position, etc.)"
    )
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['attempt', 'event_type']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.attempt.user.username} - {self.event_type} - {self.timestamp}"
    
    @classmethod
    def cleanup_old_snapshots(cls, days=30):
        """Delete proctoring data older than specified days"""
        cutoff_date = timezone.now() - timedelta(days=days)
        old_events = cls.objects.filter(timestamp__lt=cutoff_date)
        count = old_events.count()
        old_events.delete()
        return count


class PlagiarismFlag(models.Model):
    """
    Stores plagiarism detection results
    """
    attempt1 = models.ForeignKey(
        TestAttempt, 
        on_delete=models.CASCADE, 
        related_name='plagiarism_flags_as_subject'
    )
    attempt2 = models.ForeignKey(
        TestAttempt, 
        on_delete=models.CASCADE, 
        related_name='plagiarism_flags_as_comparison'
    )
    
    similarity_percentage = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    
    matching_answers = models.JSONField(
        help_text="List of question IDs with identical answers"
    )
    
    reviewed = models.BooleanField(default=False)
    reviewer_notes = models.TextField(blank=True)
    action_taken = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Action'),
            ('warning', 'Warning Issued'),
            ('disqualified', 'Candidate Disqualified'),
        ],
        default='none'
    )
    
    detected_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['reviewed', 'similarity_percentage']),
        ]
    
    def __str__(self):
        return f"{self.attempt1.user.username} vs {self.attempt2.user.username} - {self.similarity_percentage}%"
