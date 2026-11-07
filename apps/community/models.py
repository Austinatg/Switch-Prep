from django.conf import settings
from django.db import models
from django.utils import timezone

class Connection(models.Model):
    PENDING='pending'; ACCEPTED='accepted'; DECLINED='declined'
    STATUS=[(PENDING,'Pending'),(ACCEPTED,'Accepted'),(DECLINED,'Declined')]
    sender=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='sent_connections')
    receiver=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='received_connections')
    status=models.CharField(max_length=12,choices=STATUS,default=PENDING)
    created_at=models.DateTimeField(auto_now_add=True); updated_at=models.DateTimeField(auto_now=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['sender','receiver'],name='uniq_connection_direction')]
        ordering=['-created_at']
    def __str__(self): return f'{self.sender} → {self.receiver} ({self.status})'

class DailyBattle(models.Model):
    battle_date=models.DateField(unique=True,default=timezone.localdate)
    title=models.CharField(max_length=180,default='Daily Data Engineering Battle')
    description=models.TextField(blank=True)
    is_published=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self): return f'{self.title} — {self.battle_date}'

class BattleQuestion(models.Model):
    battle=models.ForeignKey(DailyBattle,on_delete=models.CASCADE,related_name='questions')
    prompt=models.TextField(); reference_answer=models.TextField(blank=True)
    display_order=models.PositiveSmallIntegerField(default=0)
    class Meta: ordering=['display_order','id']
    def __str__(self): return f'Q{self.display_order}: {self.prompt[:70]}'

class BattleSubmission(models.Model):
    battle=models.ForeignKey(DailyBattle,on_delete=models.CASCADE,related_name='submissions')
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='battle_submissions')
    submitted_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['battle','user'],name='uniq_battle_submission')]
        ordering=['-submitted_at']
    def __str__(self): return f'{self.user} — {self.battle}'

class BattleAnswer(models.Model):
    submission=models.ForeignKey(BattleSubmission,on_delete=models.CASCADE,related_name='answers')
    question=models.ForeignKey(BattleQuestion,on_delete=models.CASCADE,related_name='answers')
    answer_text=models.TextField()
    class Meta: constraints=[models.UniqueConstraint(fields=['submission','question'],name='uniq_battle_answer')]

class PeerReview(models.Model):
    submission=models.ForeignKey(BattleSubmission,on_delete=models.CASCADE,related_name='reviews')
    reviewer=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='battle_reviews')
    score=models.PositiveSmallIntegerField(default=0)
    feedback=models.CharField(max_length=500,blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['submission','reviewer'],name='uniq_peer_review')]
