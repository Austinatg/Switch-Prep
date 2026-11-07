from django import forms
from django.conf import settings


class TutorQuestionForm(forms.Form):
    LEVEL_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]
    question = forms.CharField(
        max_length=settings.DATAFORGE_AI_MAX_INPUT_CHARS,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "Ask a Data Engineering question...",
        }),
    )
    level = forms.ChoiceField(
        choices=LEVEL_CHOICES,
        initial="beginner",
        required=False,
    )

    def clean_question(self):
        question = self.cleaned_data["question"].strip()
        if not question:
            raise forms.ValidationError("Enter a question to continue.")
        return question

    def clean_level(self):
        return self.cleaned_data.get("level") or "beginner"


class CodeAssistantForm(forms.Form):
    LANGUAGE_CHOICES = [
        ("sql", "SQL"),
        ("python", "Python"),
        ("pyspark", "PySpark"),
        ("java", "Java"),
        ("other", "Other"),
    ]
    TASK_CHOICES = [
        ("explain", "Explain this code"),
        ("debug", "Find and fix a bug"),
        ("improve", "Improve code quality"),
        ("optimize", "Optimize a query or program"),
        ("review", "Review this code"),
        ("generate", "Generate an example"),
    ]

    language = forms.ChoiceField(choices=LANGUAGE_CHOICES)
    task = forms.ChoiceField(choices=TASK_CHOICES)
    code = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 12,
            "placeholder": "Paste code here. Code is analyzed as text and is never executed.",
            "spellcheck": "false",
        }),
    )
    instructions = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "What would you like help with?",
        }),
    )

    def clean(self):
        cleaned = super().clean()
        code = cleaned.get("code", "").strip()
        instructions = cleaned.get("instructions", "").strip()
        if not code and not instructions:
            raise forms.ValidationError("Provide code or describe what you need.")
        max_chars = settings.DATAFORGE_AI_MAX_INPUT_CHARS
        if len(code) + len(instructions) > max(0, max_chars - 300):
            raise forms.ValidationError(
                f"Code and instructions must leave room for the request details "
                f"within the {max_chars}-character limit."
            )
        cleaned["code"] = code
        cleaned["instructions"] = instructions
        return cleaned


class LearningRecommendationForm(forms.Form):
    interests = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.TextInput(attrs={
            "placeholder": "Optional: SQL, Spark, Azure, streaming...",
        }),
    )


class InterviewSetupForm(forms.Form):
    CATEGORY_CHOICES = [
        ("sql", "SQL"),
        ("python", "Python"),
        ("pyspark", "PySpark"),
        ("fundamentals", "Data Engineering fundamentals"),
        ("etl", "ETL and ELT"),
        ("warehousing", "Data Warehousing"),
        ("spark", "Spark"),
        ("kafka", "Kafka"),
        ("airflow", "Airflow"),
        ("cloud", "Cloud Data Engineering"),
        ("mixed", "Mixed interview"),
    ]
    DIFFICULTY_CHOICES = [
        ("beginner", "Beginner"),
        ("intermediate", "Intermediate"),
        ("advanced", "Advanced"),
    ]
    LENGTH_CHOICES = [(5, "5 questions"), (10, "10 questions"), (15, "15 questions")]

    category = forms.ChoiceField(choices=CATEGORY_CHOICES)
    difficulty = forms.ChoiceField(choices=DIFFICULTY_CHOICES)
    total_questions = forms.TypedChoiceField(
        choices=LENGTH_CHOICES,
        coerce=int,
    )


class InterviewAnswerForm(forms.Form):
    answer = forms.CharField(
        max_length=settings.DATAFORGE_AI_MAX_INPUT_CHARS,
        widget=forms.Textarea(attrs={
            "rows": 7,
            "placeholder": "Write your answer...",
        }),
    )

    def clean_answer(self):
        answer = self.cleaned_data["answer"].strip()
        if not answer:
            raise forms.ValidationError("Write an answer before submitting.")
        return answer
