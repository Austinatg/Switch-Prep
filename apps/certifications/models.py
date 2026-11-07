from django.conf import settings
from django.db import models
from django.utils.text import slugify

class CertificationTrack(models.Model):
    class Provider(models.TextChoices):
        AWS="aws","Amazon Web Services"
        AZURE="azure","Microsoft Azure"
        GCP="gcp","Google Cloud"
        DATABRICKS="databricks","Databricks"
        SNOWFLAKE="snowflake","Snowflake"
        OTHER="other","Other"
    provider=models.CharField(max_length=20,choices=Provider.choices)
    name=models.CharField(max_length=200)
    slug=models.SlugField(max_length=220,unique=True,blank=True)
    exam_code=models.CharField(max_length=80,blank=True)
    summary=models.CharField(max_length=320)
    exam_guide_url=models.URLField(max_length=1000,blank=True)
    recommended_experience=models.CharField(max_length=240,blank=True)
    domains=models.TextField(blank=True,help_text="Exam domains and their coverage; one per line.")
    is_published=models.BooleanField(default=False)
    display_order=models.PositiveSmallIntegerField(default=0)
    class Meta: ordering=["display_order","provider","name"]
    def save(self,*args,**kwargs):
        if not self.slug: self.slug=slugify(self.name)
        super().save(*args,**kwargs)
    def __str__(self): return self.name

class CertificationExam(models.Model):
    track=models.ForeignKey(CertificationTrack,on_delete=models.CASCADE,related_name="exams")
    title=models.CharField(max_length=180,default="Practice mock exam")
    instructions=models.TextField(blank=True)
    time_limit_minutes=models.PositiveSmallIntegerField(default=60)
    pass_percentage=models.PositiveSmallIntegerField(default=70)
    is_published=models.BooleanField(default=False)
    def __str__(self): return f"{self.track.name} — {self.title}"

class CertificationQuestion(models.Model):
    exam=models.ForeignKey(CertificationExam,on_delete=models.CASCADE,related_name="questions")
    prompt=models.TextField()
    explanation=models.TextField(blank=True)
    display_order=models.PositiveSmallIntegerField(default=0)
    class Meta: ordering=["display_order","id"]
    def __str__(self): return self.prompt[:100]

class CertificationChoice(models.Model):
    question=models.ForeignKey(CertificationQuestion,on_delete=models.CASCADE,related_name="choices")
    text=models.CharField(max_length=500)
    is_correct=models.BooleanField(default=False)
    display_order=models.PositiveSmallIntegerField(default=0)
    class Meta: ordering=["display_order","id"]
    def __str__(self): return self.text[:100]

class CertificationAttempt(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="certification_attempts")
    exam=models.ForeignKey(CertificationExam,on_delete=models.CASCADE,related_name="attempts")
    score=models.PositiveSmallIntegerField(default=0)
    total_questions=models.PositiveSmallIntegerField(default=0)
    percentage=models.PositiveSmallIntegerField(default=0)
    passed=models.BooleanField(default=False)
    answers=models.JSONField(default=dict,blank=True)
    submitted_at=models.DateTimeField(auto_now_add=True)
    class Meta: ordering=["-submitted_at"]
    def __str__(self): return f"{self.user} — {self.exam} — {self.percentage}%"
