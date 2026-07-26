from django import forms

from .models import SatisfactionSurvey


class SatisfactionSurveyForm(forms.ModelForm):
    """فرم عمومی نظرسنجی رضایت مشتری (بدون نیاز به ورود، از طریق لینک فرصت فروش)"""

    class Meta:
        model = SatisfactionSurvey
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.RadioSelect,
            "comment": forms.Textarea(attrs={"class": "input-field", "rows": 4, "placeholder": "نظر شما (اختیاری)"}),
        }
