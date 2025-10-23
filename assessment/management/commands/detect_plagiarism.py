"""
Management command to detect plagiarism between test attempts
Run: python manage.py detect_plagiarism
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from assessment.models import TestAttempt, Answer, PlagiarismFlag
from itertools import combinations


class Command(BaseCommand):
    help = 'Detect plagiarism by comparing test attempts'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--test-id',
            type=int,
            help='Only check attempts for specific test ID'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=70.0,
            help='Similarity threshold percentage (default: 70)'
        )
        parser.add_argument(
            '--session',
            action='store_true',
            help='Only compare within same test session'
        )
    
    def handle(self, *args, **options):
        test_id = options.get('test_id')
        threshold = options.get('threshold')
        session_only = options.get('session')
        
        self.stdout.write(self.style.SUCCESS(f'Starting plagiarism detection (threshold: {threshold}%)'))
        
        # Get completed attempts to check
        attempts_query = TestAttempt.objects.filter(status='completed')
        
        if test_id:
            attempts_query = attempts_query.filter(test_id=test_id)
            self.stdout.write(f'Filtering by test ID: {test_id}')
        
        attempts = list(attempts_query)
        self.stdout.write(f'Found {len(attempts)} completed attempts to analyze')
        
        if len(attempts) < 2:
            self.stdout.write(self.style.WARNING('Need at least 2 attempts to compare'))
            return
        
        detected_count = 0
        checked_count = 0
        
        # Group by test if session_only
        if session_only:
            from collections import defaultdict
            test_groups = defaultdict(list)
            for attempt in attempts:
                test_groups[attempt.test_id].append(attempt)
            
            for test_id, test_attempts in test_groups.items():
                self.stdout.write(f'\nChecking test ID {test_id} ({len(test_attempts)} attempts)')
                count = self.check_attempts_group(test_attempts, threshold)
                detected_count += count
                checked_count += len(list(combinations(test_attempts, 2)))
        else:
            detected_count = self.check_attempts_group(attempts, threshold)
            checked_count = len(list(combinations(attempts, 2)))
        
        self.stdout.write(self.style.SUCCESS(
            f'\nPlagiarism detection complete: {detected_count} suspicious pairs found out of {checked_count} comparisons'
        ))
    
    def check_attempts_group(self, attempts, threshold):
        """Check all pairs in a group of attempts"""
        detected_count = 0
        
        # Compare all pairs
        for attempt1, attempt2 in combinations(attempts, 2):
            # Skip if already flagged
            if PlagiarismFlag.objects.filter(
                Q(attempt1=attempt1, attempt2=attempt2) |
                Q(attempt1=attempt2, attempt2=attempt1)
            ).exists():
                continue
            
            # Calculate similarity
            similarity, matching_answers = self.calculate_similarity(attempt1, attempt2)
            
            if similarity >= threshold:
                # Create plagiarism flag
                PlagiarismFlag.objects.create(
                    attempt1=attempt1,
                    attempt2=attempt2,
                    similarity_percentage=similarity,
                    matching_answers=matching_answers
                )
                
                # Flag both attempts
                attempt1.flagged_for_plagiarism = True
                attempt1.similarity_score = max(attempt1.similarity_score or 0, similarity)
                attempt1.save()
                
                attempt2.flagged_for_plagiarism = True
                attempt2.similarity_score = max(attempt2.similarity_score or 0, similarity)
                attempt2.save()
                
                self.stdout.write(self.style.WARNING(
                    f'🚨 Plagiarism detected: {attempt1.user.username} vs {attempt2.user.username} '
                    f'({similarity:.1f}% similar)'
                ))
                
                detected_count += 1
        
        return detected_count
    
    def calculate_similarity(self, attempt1, attempt2):
        """
        Calculate similarity between two test attempts
        Returns (similarity_percentage, list_of_matching_question_ids)
        """
        # Get all answers for both attempts
        answers1 = {
            answer.question_id: answer.selected_answer
            for answer in attempt1.answers.all()
            if answer.selected_answer
        }
        
        answers2 = {
            answer.question_id: answer.selected_answer
            for answer in attempt2.answers.all()
            if answer.selected_answer
        }
        
        # Find common questions
        common_questions = set(answers1.keys()) & set(answers2.keys())
        
        if not common_questions:
            return 0.0, []
        
        # Count matching answers
        matching_answers = [
            qid for qid in common_questions
            if answers1[qid] == answers2[qid]
        ]
        
        # Calculate similarity percentage
        similarity = (len(matching_answers) / len(common_questions)) * 100
        
        return similarity, matching_answers
