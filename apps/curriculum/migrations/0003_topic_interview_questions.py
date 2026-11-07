from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("curriculum", "0002_phase4_learning_features"),
    ]

    operations = [
        migrations.AddField(
            model_name="topic",
            name="interview_questions",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of interview questions and answers for this lesson."
            ),
        ),
    ]