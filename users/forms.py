from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class ResidentRegistrationForm(UserCreationForm):
    data_privacy_consent = forms.BooleanField(
        required=True,
        label="I agree to the Data Privacy Terms and Conditions",
        help_text="By checking this, you agree to our data collection and processing policies."
    )
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'data_privacy_consent')

class BarangayRegistrationForm(UserCreationForm):
    barangay_name = forms.CharField(max_length=100)
    municipality = forms.CharField(max_length=100, initial='Ormoc City')
    captain_name = forms.CharField(max_length=100)
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email')

    def clean_barangay_name(self):
        name = self.cleaned_data.get('barangay_name', '').strip()
        from residents.models import Barangay
        if Barangay.objects.filter(name=name).exists():
            raise forms.ValidationError("This barangay is already registered.")
        return name

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('role', 'barangay_name')
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'barangay_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['role', 'is_active', 'barangay_name']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'barangay_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
