from django import forms
from .models import NotePoint

class NotePointForm(forms.ModelForm):
    class Meta:
        model = NotePoint
        fields = ["content", "importance"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 3, "placeholder": "Write one clear learning point..."}),
            "importance": forms.Select(),
        }
    def clean_content(self):
        value = self.cleaned_data["content"].strip()
        if not value:
            raise forms.ValidationError("A note point cannot be empty.")
        return value
