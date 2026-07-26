"""ویو عمومی نظرسنجی رضایت مشتری - بدون نیاز به ورود، از طریق لینک فرصت فروش قابل دسترسی است."""
from django.shortcuts import render, get_object_or_404

from .forms import SatisfactionSurveyForm
from .models import Deal


def survey_submit(request, pk):
    deal = get_object_or_404(Deal, pk=pk)

    if hasattr(deal, "survey"):
        return render(request, "crm/survey_form.html", {"deal": deal, "already_submitted": True})

    if request.method == "POST":
        form = SatisfactionSurveyForm(request.POST)
        if form.is_valid():
            survey = form.save(commit=False)
            survey.deal = deal
            survey.save()
            return render(request, "crm/survey_form.html", {"deal": deal, "submitted": True})
    else:
        form = SatisfactionSurveyForm()

    return render(request, "crm/survey_form.html", {"deal": deal, "form": form})
