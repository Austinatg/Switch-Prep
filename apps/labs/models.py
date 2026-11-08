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
    subcategory=models.CharField(max_length=100, blank=True)
    difficulty=models.CharField(max_length=20, choices=Difficulty.choices, default=Difficulty.BEGINNER)
    summary=models.CharField(max_length=300, blank=True)
    instructions=models.TextField()
    starter_content=models.TextField(blank=True, help_text="Starter SQL, Python, or configuration text.")
    expected_output=models.TextField(blank=True, help_text="Expected result for exact-output evaluation.")
    concepts=models.JSONField(default=list, blank=True)
    dataset_definition=models.JSONField(default=dict, blank=True)
    sample_input=models.JSONField(default=dict, blank=True)
    constraints=models.TextField(blank=True)
    public_test_cases=models.JSONField(default=list, blank=True)
    hidden_test_cases=models.JSONField(default=list, blank=True)
    reference_solution=models.TextField(blank=True)
    time_complexity=models.CharField(max_length=120, blank=True)
    space_complexity=models.CharField(max_length=120, blank=True)
    brute_force_explanation=models.TextField(blank=True)
    follow_up_questions=models.JSONField(default=list, blank=True)
    related_questions=models.JSONField(default=list, blank=True)
    execution_mode=models.CharField(max_length=20, default="reading", blank=True)
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


class LabDraft(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="lab_drafts")
    lab=models.ForeignKey(Lab,on_delete=models.CASCADE,related_name="drafts")
    content=models.TextField(blank=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=["-updated_at"]
        constraints=[models.UniqueConstraint(fields=["user","lab"],name="uniq_lab_draft_per_user")]
    def __str__(self): return f"Draft: {self.user} — {self.lab}"


class LabBookmark(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="lab_bookmarks")
    lab=models.ForeignKey(Lab,on_delete=models.CASCADE,related_name="bookmarks")
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=["-created_at"]
        constraints=[models.UniqueConstraint(fields=["user","lab"],name="uniq_lab_bookmark_per_user")]
    def __str__(self): return f"Bookmark: {self.user} — {self.lab}"


class LabAchievement(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="lab_achievements")
    key=models.CharField(max_length=60)
    title=models.CharField(max_length=120)
    description=models.CharField(max_length=300)
    earned_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=["-earned_at"]
        constraints=[models.UniqueConstraint(fields=["user","key"],name="uniq_lab_achievement_per_user")]
    def __str__(self): return f"{self.title}: {self.user}"


class CaseStudy(models.Model):
    class Difficulty(models.TextChoices):
        BEGINNER="beginner","Beginner"
        INTERMEDIATE="intermediate","Intermediate"
        ADVANCED="advanced","Advanced"
    title=models.CharField(max_length=180)
    slug=models.SlugField(max_length=200,unique=True,blank=True)
    summary=models.CharField(max_length=300)
    track=models.CharField(max_length=20,choices=Lab.Category.choices,default=Lab.Category.ETL)
    difficulty=models.CharField(max_length=20,choices=Difficulty.choices,default=Difficulty.INTERMEDIATE)
    requirements=models.TextField()
    dataset_definition=models.JSONField(default=dict,blank=True)
    tasks=models.JSONField(default=list,blank=True)
    checkpoints=models.JSONField(default=list,blank=True)
    expected_outcomes=models.TextField()
    display_order=models.PositiveIntegerField(default=0)
    is_published=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        ordering=["display_order","title"]
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
