from django import forms


class PropertyFilterForm(forms.Form):
    """Validate numeric filters before they reach PostgreSQL integer columns."""

    min_price = forms.IntegerField(required=False, min_value=0, max_value=2**63 - 1)
    max_price = forms.IntegerField(required=False, min_value=0, max_value=2**63 - 1)
    min_area = forms.IntegerField(required=False, min_value=0, max_value=2**31 - 1)
    max_area = forms.IntegerField(required=False, min_value=0, max_value=2**31 - 1)
    rooms = forms.IntegerField(required=False, min_value=0, max_value=2**15 - 1)

    def clean(self):
        cleaned_data = super().clean()
        for field in ("price", "area"):
            lower, upper = f"min_{field}", f"max_{field}"
            minimum, maximum = cleaned_data.get(lower), cleaned_data.get(upper)
            if minimum is not None and maximum is not None and minimum > maximum:
                # Ignore an invalid range while keeping unrelated valid filters.
                for bound in (lower, upper):
                    self.add_error(bound, "حداقل نباید بیشتر از حداکثر باشد.")
        return cleaned_data
