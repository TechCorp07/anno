"""
Management command to generate DICOM anatomy identification questions
Usage: python manage.py generate_dicom_questions
"""

from django.core.management.base import BaseCommand
from assessment.models import TestCategory, QuestionTopic, Question
import json


class Command(BaseCommand):
    help = 'Generate DICOM anatomy identification questions for MRI training'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Generating DICOM questions...'))
        
        # Get or create category and topic
        category, _ = TestCategory.objects.get_or_create(
            name='MRI Anatomy Identification',
            defaults={
                'description': 'Identify anatomical structures on MRI images',
                'stage_number': 3,
                'passing_score': 75
            }
        )
        
        topic, _ = QuestionTopic.objects.get_or_create(
            category=category,
            name='Brain MRI Anatomy',
            defaults={
                'description': 'Identify brain structures on T1 and T2 weighted images',
                'questions_per_test': 10
            }
        )
        
        # Generate questions
        questions = self.generate_brain_questions(topic)
        
        created_count = 0
        for q_data in questions:
            question, created = Question.objects.get_or_create(
                topic=topic,
                question_text=q_data['question_text'],
                defaults={
                    'question_type': 'dicom',
                    'hotspot_coordinates': q_data['hotspots'],
                    'explanation': q_data['explanation'],
                    'difficulty_level': q_data['difficulty'],
                    'time_limit_seconds': 120,
                    'points': q_data['difficulty'],
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Created {created_count} DICOM questions')
        )
        self.stdout.write(
            self.style.WARNING('\n⚠️  IMPORTANT: You need to upload actual DICOM images!')
        )
        self.stdout.write('Instructions:')
        self.stdout.write('1. Place DICOM files in: media/dicom/')
        self.stdout.write('2. In Django admin, edit each question and attach the DICOM file')
        self.stdout.write('3. Hotspot coordinates are already configured\n')

    def generate_brain_questions(self, topic):
        """Generate brain anatomy identification questions"""
        
        questions = [
            {
                'question_text': 'Identify the corpus callosum on this sagittal T1-weighted brain MRI.',
                'hotspots': [
                    {'x': 250, 'y': 180, 'width': 120, 'height': 30, 'label': 'Corpus Callosum'}
                ],
                'explanation': 'The corpus callosum is the large white matter structure connecting the cerebral hemispheres.',
                'difficulty': 2
            },
            {
                'question_text': 'Click on the cerebellum in this sagittal brain MRI.',
                'hotspots': [
                    {'x': 200, 'y': 350, 'width': 150, 'height': 120, 'label': 'Cerebellum'}
                ],
                'explanation': 'The cerebellum is located in the posterior cranial fossa, inferior to the cerebrum.',
                'difficulty': 1
            },
            {
                'question_text': 'Identify the lateral ventricles on this axial T2-weighted brain MRI.',
                'hotspots': [
                    {'x': 180, 'y': 200, 'width': 80, 'height': 60, 'label': 'Left Lateral Ventricle'},
                    {'x': 340, 'y': 200, 'width': 80, 'height': 60, 'label': 'Right Lateral Ventricle'}
                ],
                'explanation': 'The lateral ventricles appear as bright CSF-filled spaces on T2-weighted images.',
                'difficulty': 2
            },
            {
                'question_text': 'Locate the pituitary gland on this sagittal T1-weighted image.',
                'hotspots': [
                    {'x': 280, 'y': 260, 'width': 40, 'height': 35, 'label': 'Pituitary Gland'}
                ],
                'explanation': 'The pituitary gland sits in the sella turcica, connected to the hypothalamus by the infundibulum.',
                'difficulty': 3
            },
            {
                'question_text': 'Identify the brainstem on this sagittal brain MRI.',
                'hotspots': [
                    {'x': 240, 'y': 280, 'width': 60, 'height': 100, 'label': 'Brainstem'}
                ],
                'explanation': 'The brainstem consists of the midbrain, pons, and medulla oblongata.',
                'difficulty': 2
            },
            {
                'question_text': 'Click on the thalamus on this axial T1-weighted brain MRI.',
                'hotspots': [
                    {'x': 220, 'y': 240, 'width': 50, 'height': 45, 'label': 'Left Thalamus'},
                    {'x': 330, 'y': 240, 'width': 50, 'height': 45, 'label': 'Right Thalamus'}
                ],
                'explanation': 'The thalamus is a paired gray matter structure located medial to the internal capsule.',
                'difficulty': 3
            },
            {
                'question_text': 'Identify the frontal lobe on this sagittal brain MRI.',
                'hotspots': [
                    {'x': 300, 'y': 120, 'width': 140, 'height': 180, 'label': 'Frontal Lobe'}
                ],
                'explanation': 'The frontal lobe is the anterior-most lobe of the cerebrum.',
                'difficulty': 1
            },
            {
                'question_text': 'Locate the fourth ventricle on this sagittal T2-weighted brain image.',
                'hotspots': [
                    {'x': 220, 'y': 310, 'width': 45, 'height': 50, 'label': 'Fourth Ventricle'}
                ],
                'explanation': 'The fourth ventricle is located between the brainstem and cerebellum.',
                'difficulty': 2
            },
            {
                'question_text': 'Click on the caudate nucleus on this axial T1-weighted image.',
                'hotspots': [
                    {'x': 200, 'y': 220, 'width': 40, 'height': 55, 'label': 'Left Caudate'},
                    {'x': 360, 'y': 220, 'width': 40, 'height': 55, 'label': 'Right Caudate'}
                ],
                'explanation': 'The caudate nucleus forms the lateral wall of the lateral ventricles.',
                'difficulty': 3
            },
            {
                'question_text': 'Identify the temporal lobe on this axial brain MRI.',
                'hotspots': [
                    {'x': 120, 'y': 320, 'width': 110, 'height': 90, 'label': 'Left Temporal Lobe'},
                    {'x': 370, 'y': 320, 'width': 110, 'height': 90, 'label': 'Right Temporal Lobe'}
                ],
                'explanation': 'The temporal lobes are located lateral and inferior in the cerebrum.',
                'difficulty': 1
            },
            {
                'question_text': 'Locate the hippocampus on this coronal T2-weighted brain MRI.',
                'hotspots': [
                    {'x': 180, 'y': 340, 'width': 45, 'height': 35, 'label': 'Left Hippocampus'},
                    {'x': 375, 'y': 340, 'width': 45, 'height': 35, 'label': 'Right Hippocampus'}
                ],
                'explanation': 'The hippocampus is part of the limbic system, located in the medial temporal lobe.',
                'difficulty': 4
            },
            {
                'question_text': 'Identify the splenium of the corpus callosum on this sagittal image.',
                'hotspots': [
                    {'x': 220, 'y': 185, 'width': 50, 'height': 35, 'label': 'Splenium'}
                ],
                'explanation': 'The splenium is the posterior bulbous portion of the corpus callosum.',
                'difficulty': 3
            },
            {
                'question_text': 'Click on the optic chiasm on this coronal T1-weighted image.',
                'hotspots': [
                    {'x': 300, 'y': 270, 'width': 40, 'height': 25, 'label': 'Optic Chiasm'}
                ],
                'explanation': 'The optic chiasm is located superior to the pituitary gland where optic nerves cross.',
                'difficulty': 4
            },
            {
                'question_text': 'Identify the occipital lobe on this sagittal brain MRI.',
                'hotspots': [
                    {'x': 140, 'y': 180, 'width': 100, 'height': 130, 'label': 'Occipital Lobe'}
                ],
                'explanation': 'The occipital lobe is the posterior-most lobe, responsible for visual processing.',
                'difficulty': 1
            },
            {
                'question_text': 'Locate the pineal gland on this sagittal T1-weighted brain image.',
                'hotspots': [
                    {'x': 250, 'y': 200, 'width': 25, 'height': 25, 'label': 'Pineal Gland'}
                ],
                'explanation': 'The pineal gland is a small endocrine gland located posterior to the third ventricle.',
                'difficulty': 4
            },
            {
                'question_text': 'Identify the internal capsule on this axial T1-weighted image.',
                'hotspots': [
                    {'x': 240, 'y': 250, 'width': 30, 'height': 50, 'label': 'Left Internal Capsule'},
                    {'x': 330, 'y': 250, 'width': 30, 'height': 50, 'label': 'Right Internal Capsule'}
                ],
                'explanation': 'The internal capsule is a white matter structure containing motor and sensory pathways.',
                'difficulty': 3
            },
            {
                'question_text': 'Click on the third ventricle on this coronal T2-weighted brain MRI.',
                'hotspots': [
                    {'x': 300, 'y': 250, 'width': 35, 'height': 60, 'label': 'Third Ventricle'}
                ],
                'explanation': 'The third ventricle is a midline CSF-filled space between the thalami.',
                'difficulty': 2
            },
            {
                'question_text': 'Identify the putamen on this axial T1-weighted brain image.',
                'hotspots': [
                    {'x': 210, 'y': 260, 'width': 45, 'height': 50, 'label': 'Left Putamen'},
                    {'x': 345, 'y': 260, 'width': 45, 'height': 50, 'label': 'Right Putamen'}
                ],
                'explanation': 'The putamen is part of the basal ganglia, lateral to the globus pallidus.',
                'difficulty': 3
            },
            {
                'question_text': 'Locate the pons on this sagittal T1-weighted brain MRI.',
                'hotspots': [
                    {'x': 245, 'y': 295, 'width': 55, 'height': 45, 'label': 'Pons'}
                ],
                'explanation': 'The pons is the middle portion of the brainstem, anterior to the cerebellum.',
                'difficulty': 2
            },
            {
                'question_text': 'Identify the sylvian fissure on this axial brain MRI.',
                'hotspots': [
                    {'x': 150, 'y': 280, 'width': 80, 'height': 25, 'label': 'Left Sylvian Fissure'},
                    {'x': 370, 'y': 280, 'width': 80, 'height': 25, 'label': 'Right Sylvian Fissure'}
                ],
                'explanation': 'The Sylvian fissure (lateral sulcus) separates the temporal from frontal and parietal lobes.',
                'difficulty': 2
            },
        ]
        
        return questions


# Additional command for spine questions
    def generate_spine_questions(self, topic):
        """Generate spine anatomy questions"""
        questions = [
            {
                'question_text': 'Identify the C5 vertebral body on this sagittal cervical spine MRI.',
                'hotspots': [
                    {'x': 280, 'y': 300, 'width': 60, 'height': 45, 'label': 'C5 Vertebral Body'}
                ],
                'explanation': 'C5 is the fifth cervical vertebra from the top.',
                'difficulty': 2
            },
            {
                'question_text': 'Click on the spinal cord on this sagittal T2-weighted spine image.',
                'hotspots': [
                    {'x': 260, 'y': 200, 'width': 40, 'height': 250, 'label': 'Spinal Cord'}
                ],
                'explanation': 'The spinal cord appears as a tubular structure within the spinal canal.',
                'difficulty': 1
            },
        ]
        return questions