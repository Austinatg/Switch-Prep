from django.conf import settings
from django.db import models
from django.utils.text import slugify

class Lab(models.Model):
    class Category(models.TextChoices):
        SQL="sql", "SQL"
        PYTHON="python", "Python"
        PYSPARK="pyspark", "PySpark"
        ETL="etl", "ETL / Pipelines"
        CLOUD="cloud", "Cloud Data Engineering"
    class Difficulty(models.TextChoices):
        BEGINNER="beginner", "Beginner"
        INTERMEDIATE="intermediate", "Intermediate"
        ADVANCED="advanced", "Advanced"
    class Evaluation(models.TextChoices):
        EXACT="exact", "Exact output match"
        KEYWORDS="keywords", "Required keywords"
        REVIEW="review", "Manual review"
    title=models.CharField(max_length=180)
    slug=models.SlugField(max_length=200, unique=True, blank=True)
    category=models.CharField(max_length=20, choices=Category.choices)
    difficulty=models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.BEGINNER)
    summary=models.CharField(max_length=300, blank=True)
    instructions=models.TextField()
    starter_content=models.TextField(blank=True, help_text="Starter SQL, Python, or configuration text.")
    expected_output=models.TextField(blank=True, help_text="Expected result for exact-output evaluation.")
    required_keywords=models.JSONField(default=list, blank=True)
    evaluation_type=models.CharField(max_length=20, choices=Evaluation.choices, default=Evaluation.REVIEW)
    hints=models.TextField(blank=True, help_text="One hint per line.")
    estimated_minutes=models.PositiveSmallIntegerField(default=30)
    display_order=models.PositiveIntegerField(default=0)
    is_published=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["display_order","title"]
    def save(self,*args,**kwargs):
        if not self.slug: self.slug=slugify(self.title)
        super().save(*args,**kwargs)
    def __str__(self): return self.title

class LabAttempt(models.Model):
    class Status(models.TextChoices):
        SUBMITTED="submitted", "Submitted"
        PASSED="passed", "Passed"
        NEEDS_REVIEW="needs_review", "Needs review"
        REVIEWED="reviewed", "Reviewed"
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="lab_attempts")
    lab=models.ForeignKey(Lab,on_delete=models.CASCADE,related_name="attempts")
    answer=models.TextField()
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.SUBMITTED)
    score=models.PositiveSmallIntegerField(default=0)
    feedback=models.TextField(blank=True)
    evaluation_details=models.JSONField(default=dict,blank=True)
    submitted_at=models.DateTimeField(auto_now_add=True)
    reviewed_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=["-submitted_at"]
    def __str__(self): return f"{self.user} — {self.lab} — {self.status}"
