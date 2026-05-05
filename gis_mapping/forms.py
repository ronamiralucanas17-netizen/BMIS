from django import forms
from leaflet.forms.fields import PolygonField
from .models import Infrastructure, DisasterProneArea, EvacuationSite

class InfrastructureForm(forms.ModelForm):
    latitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Latitude', 'readonly': 'readonly'})
    )
    longitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Longitude', 'readonly': 'readonly'})
    )

    class Meta:
        model = Infrastructure
        fields = ['name', 'type', 'barangay_ref']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'barangay_ref': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make barangay_ref optional in form because we might set it in view
        self.fields['barangay_ref'].required = False

class DisasterProneAreaForm(forms.ModelForm):
    boundary_json = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'id': 'boundary_json_input', 'readonly': 'readonly'})
    )

    class Meta:
        model = DisasterProneArea
        fields = ['name', 'type', 'risk_level', 'barangay_ref', 'boundary']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
            'barangay_ref': forms.Select(attrs={'class': 'form-select'}),
        }

class EvacuationSiteForm(forms.ModelForm):
    latitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Latitude', 'readonly': 'readonly'})
    )
    longitude = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Longitude', 'readonly': 'readonly'})
    )

    class Meta:
        model = EvacuationSite
        fields = ['name', 'barangay', 'capacity']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'barangay': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make barangay optional in form because we might set it in view
        self.fields['barangay'].required = False
