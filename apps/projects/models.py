from django.conf import settings
from django.db import models
from django.utils.text import slugify

class Project(models.Model):
    class Level(models.TextChoices):
        BEGINNER="beginner","Beginner"
        INTERMEDIATE="intermediate","Intermediate"
        ADVANCED="advanced","Advanced"
    title=models.CharField(max_length=200)
    slug=models.SlugField(max_length=220,unique=True,blank=True)
    summary=models.CharField(max_length=320)
    description=models.TextField()
    learning_outcomes=models.TextField(blank=True,help_text="One outcome per line.")
    architecture_notes=models.TextField(blank=True,help_text="Architecture and production considerations.")
    level=models.CharField(max_length=20,choices=Level.choices,default=Level.BEGINNER)
    estimated_days=models.PositiveSmallIntegerField(default=7)
    is_capstone=models.BooleanField(default=False)
    is_published=models.BooleanField(default=False)
    display_order=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: ordering=["display_order","title"]
    def save(self,*args,**kwargs):
        if not self.slug: self.slug=slugify(self.title)
        super().save(*args,**kwargs)
    def __str__(self): return self.title

class ProjectMilestone(models.Model):
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name="milestones")
    title=models.CharField(max_length=180)
    instructions=models.TextField()
    acceptance_criteria=models.TextField(blank=True,help_text="One criterion per line.")
    display_order=models.PositiveSmallIntegerField(default=0)
    class Meta: ordering=["display_order","id"]
    def __str__(self): return f"{self.project.title} — {self.title}"

class ProjectEnrollment(models.Model):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="project_enrollments")
    project=models.ForeignKey(Project,on_delete=models.CASCADE,related_name="enrollments")
    enrolled_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=["user","project"],name="uniq_user_project_enrollment")]
        ordering=["-enrolled_at"]
    def __str__(self): return f"{self.user} — {self.project}"

class MilestoneSubmission(models.Model):
    class Status(models.TextChoices):
        SUBMITTED="submitted","Submitted"
        APPROVED="approved","Approved"
        REVISION="revision","Revision requested"
    enrollment=models.ForeignKey(ProjectEnrollment,on_delete=models.CASCADE,related_name="submissions")
    milestone=models.ForeignKey(ProjectMilestone,on_delete=models.CASCADE,related_name="submissions")
    submission_text=models.TextField(help_text="Describe your implementation and decisions.")
    artifact_url=models.URLField(max_length=1000,blank=True)
    status=models.CharField(max_length=20,choices=Status.choices,default=Status.SUBMITTED)
    reviewer_feedback=models.TextField(blank=True)
    submitted_at=models.DateTimeField(auto_now_add=True)
    reviewed_at=models.DateTimeField(null=True,blank=True)
    class Meta: ordering=["-submitted_at"]
    def __str__(self): return f"{self.enrollment} — {self.milestone}"
