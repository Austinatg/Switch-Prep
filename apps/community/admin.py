from django.contrib import admin
from .models import Connection,DailyBattle,BattleQuestion,BattleSubmission,BattleAnswer,PeerReview
class QuestionInline(admin.TabularInline): model=BattleQuestion; extra=1
@admin.register(DailyBattle)
class DailyBattleAdmin(admin.ModelAdmin): list_display=('title','battle_date','is_published'); list_filter=('is_published','battle_date'); inlines=[QuestionInline]
admin.site.register([Connection,BattleSubmission,BattleAnswer,PeerReview])
