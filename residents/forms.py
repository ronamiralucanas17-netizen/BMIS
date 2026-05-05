from django import forms
from .models import Resident, Household, ResidentDocument, Official, Service, ServiceRequest, IncidentReport, Barangay, Announcement
from django.contrib.auth import get_user_model

User = get_user_model()
from leaflet.forms.widgets import LeafletWidget
from django.contrib.gis.geos import Point

class ResidentsExcelUploadForm(forms.Form):
    file = forms.FileField(widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'}))

class ProfileCompletionForm(forms.ModelForm):
    # Optional fields for creating a new household
    new_household_number = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter new household number'}))
    no_household_number = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}), label="I don't have a household number")
    new_household_address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Enter full address'}), required=False)
    new_barangay = forms.ModelChoiceField(
        queryset=Barangay.objects.filter(is_approved=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select your barangay",
        label="Barangay",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Explicitly make fields required for profile completion
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['date_of_birth'].required = True
        self.fields['gender'].required = True
        self.fields['civil_status'].required = True
        self.fields['residency_status'].required = True
        self.fields['current_location'].required = True
        self.fields['present_address'].required = True
        self.fields['residency_type'].required = True
        # Make existing household field optional to allow manual input
        self.fields['household'].required = False

        # Update labels for education fields
        self.fields['elementary_school'].label = "Elementary school where he or she attended"
        self.fields['high_school'].label = "Highschool attended"
        self.fields['college'].label = "College attended"

        if self.instance and self.instance.pk and self.instance.profile_status == 'INCOMPLETE':
            # 1. Base required fields for everyone
            required_fields = [
                'photo', 'first_name', 'last_name', 'date_of_birth', 'gender', 
                'civil_status', 'residency_status', 'present_address', 
                'residency_type', 'contact_number', 'household', 
                'birthplace', 'citizenship', 'religion', 'years_in_barangay', 
                'father_name', 'mother_maiden_name', 'zone_street_purok',
                'current_location',
            ]
            
            # 2. Conditional: If NOT a student, these are required
            if not self.instance.is_student:
                required_fields.extend([
                    'educational_attainment', 'occupation', 'income', 'employment_status'
                ])
            else:
                # If IS a student, these are required
                required_fields.append('student_level')
                level = (self.instance.student_level or '').upper()
                if level == 'ELEMENTARY':
                    required_fields.append('elementary_school')
                elif level in ['HIGHSCHOOL', 'HIGH SCHOOL']:
                    required_fields.append('high_school')
                elif level == 'COLLEGE':
                    required_fields.append('college')

            # 3. Permanent address (if not same as present)
            if not getattr(self.instance, 'is_present_address_same_as_permanent', False):
                required_fields.append('permanent_address')
            
            # 4. Other conditional requirements
            if self.instance.civil_status in ['MARRIED', 'SEPARATED', 'WIDOWED', 'DIVORCED', 'LIVE_IN']:
                required_fields.append('spouse_name')
            if self.instance.has_children:
                required_fields.append('num_children')

            if self.instance.current_location == 'AWAY':
                required_fields.extend(['away_duration_years', 'away_duration_months'])
            
            highlighted_any = False
            for field_name in required_fields:
                if field_name in self.fields:
                    # Skip permanent_address if same as present is checked
                    if field_name == 'permanent_address' and getattr(self.instance, 'is_present_address_same_as_permanent', False):
                        continue

                    value = getattr(self.instance, field_name, None)
                    # Check for empty strings, None, or empty related objects
                    is_empty = False
                    if not value: # This catches None, empty strings, empty lists, empty FieldFiles
                        is_empty = True
                    elif isinstance(value, str) and not value.strip():
                        is_empty = True
                    elif hasattr(value, 'exists') and not value.exists(): # For QuerySets
                        is_empty = True
                    
                    # Special check for ImageField/FileField
                    if field_name == 'photo':
                        try:
                            # Safely check if photo exists without triggering ValueError
                            if not value or not hasattr(value, 'url') or not value.name:
                                is_empty = True
                        except (ValueError, AttributeError):
                            is_empty = True

                    if is_empty:
                        # Add highlight class and title
                        existing_classes = self.fields[field_name].widget.attrs.get('class', '')
                        if 'is-invalid-highlight' not in existing_classes:
                            self.fields[field_name].widget.attrs['class'] = f"{existing_classes} is-invalid-highlight".strip()
                        self.fields[field_name].widget.attrs['title'] = "Need to fill up"
                        self.fields[field_name].help_text = "This field needs to be filled up to complete your profile."
                        highlighted_any = True
            
    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        dob = cleaned_data.get('date_of_birth')

        if first_name and last_name and dob:
            # Check if another user already claimed this resident profile
            # We allow claimable profiles (user__isnull=True) because the view handles linking them.
            queryset = Resident.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                date_of_birth=dob,
                user__isnull=False
            )
            
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise forms.ValidationError(
                    "A resident with this name and date of birth is already registered with an account. Please contact your barangay office if you believe this is an error."
                )

        household = cleaned_data.get('household')
        new_hh_num = cleaned_data.get('new_household_number')
        no_hh_num = cleaned_data.get('no_household_number')
        new_hh_addr = cleaned_data.get('new_household_address')
        new_brgy = cleaned_data.get('new_barangay')
        
        is_same = cleaned_data.get('is_present_address_same_as_permanent')
        present = cleaned_data.get('present_address')
        
        if is_same and not present:
            self.add_error('present_address', "Present address is required if it's the same as permanent.")

        if not household:
            if not no_hh_num and not new_hh_num:
                raise forms.ValidationError("Please either select an existing household, provide a new number, or check 'I don't have a household number'.")
            
            if not all([new_hh_addr, new_brgy]):
                raise forms.ValidationError("Address and Barangay are required for new household registrations.")
            
            # Check if household number already exists (if provided)
            if new_hh_num and Household.objects.filter(household_number=new_hh_num).exists():
                raise forms.ValidationError(f"Household number {new_hh_num} already exists. Please select it from the list or use a different number.")
        
        if cleaned_data.get('has_children'):
            num_children = cleaned_data.get('num_children')
            if not num_children or num_children <= 0:
                self.add_error('num_children', "Please specify the number of children.")

        current_location = cleaned_data.get('current_location')
        away_years = cleaned_data.get('away_duration_years') or 0
        away_months = cleaned_data.get('away_duration_months') or 0
        if current_location == 'AWAY':
            if away_years < 0:
                self.add_error('away_duration_years', "Must be 0 or greater.")
            if away_months < 0 or away_months > 11:
                self.add_error('away_duration_months', "Must be between 0 and 11.")
            if away_years == 0 and away_months == 0:
                self.add_error('away_duration_months', "Please indicate how long you have been away (years or months).")
        else:
            cleaned_data['away_duration_years'] = 0
            cleaned_data['away_duration_months'] = 0

        employment_status = cleaned_data.get('employment_status')
        employment_status_other = (cleaned_data.get('employment_status_other') or '').strip()
        if employment_status == 'OTHER' and not employment_status_other:
            self.add_error('employment_status_other', "Please specify your employment status.")
        if employment_status != 'OTHER':
            cleaned_data['employment_status_other'] = ''
        
        return cleaned_data

    class Meta:
        model = Resident
        fields = [
            'photo',
            'first_name', 'last_name', 'middle_name', 
            'date_of_birth', 'birthplace', 'gender', 'civil_status', 'spouse_name',
            'citizenship', 'religion', 
            'has_children', 'num_children', 'children_details', 
            'father_name', 'is_father_deceased',
            'mother_maiden_name', 'is_mother_deceased',
            'household', 'barangay', 'zone_street_purok',
            'present_address', 'permanent_address', 'is_present_address_same_as_permanent',
            'residency_type', 'years_in_barangay',
            'contact_number', 'email', 'educational_attainment', 'occupation', 
            'income', 'employment_status', 'employment_status_other', 'is_student', 
            'student_level', 'elementary_school', 'high_school', 'college',
            'elementary_graduated_at', 'high_school_graduated_at',
            'employment_history', 'is_voter', 'residency_status',
            'current_location', 'away_duration_years', 'away_duration_months',
        ]
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control d-none', 'onchange': 'previewImage(this);'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'birthplace': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'civil_status': forms.Select(attrs={'class': 'form-select', 'onchange': 'toggleSpouseField()'}),
            'spouse_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name of Spouse'}),
            'citizenship': forms.TextInput(attrs={'class': 'form-control'}),
            'religion': forms.TextInput(attrs={'class': 'form-control'}),
            
            'has_children': forms.CheckboxInput(attrs={'class': 'form-check-input', 'onchange': 'toggleChildrenFields()'}),
            'num_children': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'How many children?', 'onchange': 'generateChildrenRows()'}),
            'children_details': forms.HiddenInput(),
            'father_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Father's Full Name"}),
            'is_father_deceased': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mother_maiden_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Mother's Maiden Name"}),
            'is_mother_deceased': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            'household': forms.Select(attrs={'class': 'form-select'}),
            'barangay': forms.Select(attrs={'class': 'form-select'}),
            'zone_street_purok': forms.TextInput(attrs={'class': 'form-control'}),
            
            'present_address': forms.TextInput(attrs={'class': 'form-control'}),
            'permanent_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank if same as present'}),
            'is_present_address_same_as_permanent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'residency_type': forms.Select(attrs={'class': 'form-select'}),
            'years_in_barangay': forms.NumberInput(attrs={'class': 'form-control'}),
            
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'educational_attainment': forms.Select(attrs={'class': 'form-select'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'income': forms.NumberInput(attrs={'class': 'form-control'}),
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'employment_status_other': forms.TextInput(attrs={'class': 'form-control'}),
            'is_student': forms.CheckboxInput(attrs={'class': 'form-check-input', 'onchange': 'toggleStudentFields()'}),
            'student_level': forms.Select(attrs={'class': 'form-select', 'onchange': 'toggleStudentLevelFields()'}),
            'elementary_school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current School'}),
            'high_school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current School'}),
            'college': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current School'}),
            'elementary_graduated_at': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School where graduated'}),
            'high_school_graduated_at': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School where graduated'}),
            'employment_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_voter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'residency_status': forms.Select(attrs={'class': 'form-select'}),
            'current_location': forms.Select(attrs={'class': 'form-select', 'onchange': 'toggleAwayFields()'}),
            'away_duration_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'away_duration_months': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 11}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = ResidentDocument
        fields = ['document', 'description']
        widgets = {
            'document': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Valid ID, Proof of Residency'})
        }

class OfficialForm(forms.ModelForm):
    resident = forms.ModelChoiceField(
        queryset=Resident.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Name',
    )

    def __init__(self, *args, **kwargs):
        barangay = kwargs.pop('barangay', None)
        super().__init__(*args, **kwargs)

        qs = Resident.objects.all()
        if barangay is not None:
            qs = qs.filter(barangay=barangay, profile_status='APPROVED', is_active=True)

        self.fields['resident'].queryset = qs.order_by('last_name', 'first_name', 'id')
        self.fields['name'].required = False
        self.fields['name'].widget = forms.HiddenInput()
        if not getattr(self.instance, 'pk', None):
            self.fields['resident'].required = True

    def clean(self):
        cleaned = super().clean()
        resident = cleaned.get('resident')
        if not getattr(self.instance, 'pk', None) and resident is None:
            self.add_error('resident', "Please select an existing resident for this official.")
        return cleaned

    def save(self, commit=True):
        official = super().save(commit=False)
        resident = self.cleaned_data.get('resident')
        if resident is not None:
            official.name = resident.full_name
        if commit:
            official.save()
        return official

    class Meta:
        model = Official
        fields = ['name', 'position', 'term_start', 'term_end', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'position': forms.Select(attrs={'class': 'form-select'}),
            'term_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'term_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'description', 'requirements', 'processing_time', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'requirements': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'processing_time': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['request_message']
        widgets = {
            'request_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Optional: Provide details about your request...'}),
        }

class ServiceRequestUpdateForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

class IncidentReportForm(forms.ModelForm):
    class Meta:
        model = IncidentReport
        fields = ['title', 'description', 'report_type', 'respondent_name', 'location_point', 'location_address']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief title of the report'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed description of the incident...'}),
            'report_type': forms.Select(attrs={'class': 'form-select'}),
            'respondent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional: Name of the person being reported'}),
            'location_point': LeafletWidget(),
            'location_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional: Specific location address'}),
        }

class IncidentResponseForm(forms.ModelForm):
    class Meta:
        model = IncidentReport
        fields = ['status', 'schedule_date', 'schedule_time', 'location']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'schedule_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'schedule_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'is_global', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_global': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class BarangayForm(forms.ModelForm):
    class Meta:
        model = Barangay
        fields = ['name', 'captain_name', 'email', 'contact_number', 'is_active', 'is_approved']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'captain_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ResidentForm(forms.ModelForm):
    # Optional fields for creating a new household manually
    new_household_number = forms.CharField(
        max_length=50, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'OR Enter new household number if not in list'})
    )
    new_household_address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Address for new household'}), 
        required=False
    )

    class Meta:
        model = Resident
        fields = [
            'photo', 'first_name', 'last_name', 'middle_name', 
            'date_of_birth', 'birthplace', 'gender', 'civil_status', 'spouse_name',
            'citizenship', 'religion', 
            'has_children', 'num_children', 'children_details', 
            'father_name', 'is_father_deceased',
            'mother_maiden_name', 'is_mother_deceased',
            'household', 'barangay', 'zone_street_purok',
            'present_address', 'permanent_address', 'is_present_address_same_as_permanent',
            'residency_type', 'years_in_barangay',
            'contact_number', 'email', 'educational_attainment', 'occupation', 
            'income', 'employment_status', 'employment_status_other', 'is_student', 
            'student_level', 'elementary_school', 'high_school', 'college',
            'elementary_graduated_at', 'high_school_graduated_at',
            'employment_history', 'is_voter', 'residency_status',
            'current_location', 'away_duration_years', 'away_duration_months',
            'profile_status',
            'is_active'
        ]
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control d-none', 'onchange': 'previewImage(this);'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'birthplace': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'civil_status': forms.Select(attrs={'class': 'form-select', 'onchange': 'toggleSpouseField()'}),
            'spouse_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name of Spouse'}),
            'citizenship': forms.TextInput(attrs={'class': 'form-control'}),
            'religion': forms.TextInput(attrs={'class': 'form-control'}),
            
            'has_children': forms.CheckboxInput(attrs={'class': 'form-check-input', 'onchange': 'toggleChildrenFields()'}),
            'num_children': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'How many children?', 'onchange': 'generateChildrenRows()'}),
            'children_details': forms.HiddenInput(),
            'father_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Father's Full Name"}),
            'is_father_deceased': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mother_maiden_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Mother's Maiden Name"}),
            'is_mother_deceased': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            'household': forms.Select(attrs={'class': 'form-select'}),
            'barangay': forms.Select(attrs={'class': 'form-select'}),
            'zone_street_purok': forms.TextInput(attrs={'class': 'form-control'}),
            
            'present_address': forms.TextInput(attrs={'class': 'form-control'}),
            'permanent_address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank if same as present'}),
            'is_present_address_same_as_permanent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'residency_type': forms.Select(attrs={'class': 'form-select'}),
            'years_in_barangay': forms.NumberInput(attrs={'class': 'form-control'}),
            
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'educational_attainment': forms.Select(attrs={'class': 'form-select'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control'}),
            'income': forms.NumberInput(attrs={'class': 'form-control'}),
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'employment_status_other': forms.TextInput(attrs={'class': 'form-control'}),
            'is_student': forms.CheckboxInput(attrs={'class': 'form-check-input', 'onchange': 'toggleStudentFields()'}),
            'student_level': forms.Select(attrs={'class': 'form-select', 'onchange': 'toggleStudentLevelFields()'}),
            'elementary_school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current School'}),
            'high_school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current School'}),
            'college': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Current School'}),
            'elementary_graduated_at': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School where graduated'}),
            'high_school_graduated_at': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'School where graduated'}),
            'employment_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_voter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'residency_status': forms.Select(attrs={'class': 'form-select'}),
            'current_location': forms.Select(attrs={'class': 'form-select'}),
            'away_duration_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'away_duration_months': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 11}),
            'profile_status': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'first_name' in self.fields:
            self.fields['first_name'].required = True
        if 'last_name' in self.fields:
            self.fields['last_name'].required = True
        if 'date_of_birth' in self.fields:
            self.fields['date_of_birth'].required = True

        # Update labels for education fields
        if 'elementary_school' in self.fields:
            self.fields['elementary_school'].label = "Elementary school where he or she attended"
        if 'high_school' in self.fields:
            self.fields['high_school'].label = "Highschool attended"
        if 'college' in self.fields:
            self.fields['college'].label = "College attended"

        for field_name, field in self.fields.items():
            if field_name in ('children_details',):
                continue
            if field.help_text:
                continue
            field.help_text = 'Required' if field.required else 'Optional'

        # Highlight empty required fields if profile is incomplete
        if self.instance and self.instance.pk and self.instance.profile_status == 'INCOMPLETE':
            # 1. Base required fields for everyone
            required_fields = [
                'photo', 'first_name', 'last_name', 'date_of_birth', 'gender', 
                'civil_status', 'residency_status', 'present_address', 
                'residency_type', 'contact_number', 'household', 
                'birthplace', 'citizenship', 'religion', 'years_in_barangay', 
                'father_name', 'mother_maiden_name', 'zone_street_purok',
                'current_location',
            ]
            
            # 2. Conditional: If NOT a student, these are required
            if not self.instance.is_student:
                required_fields.extend([
                    'educational_attainment', 'occupation', 'income', 'employment_status'
                ])
            else:
                # If IS a student, these are required
                required_fields.append('student_level')
                level = (self.instance.student_level or '').upper()
                if level == 'ELEMENTARY':
                    required_fields.append('elementary_school')
                elif level in ['HIGHSCHOOL', 'HIGH SCHOOL']:
                    required_fields.append('high_school')
                elif level == 'COLLEGE':
                    required_fields.append('college')

            # 3. Permanent address (if not same as present)
            if not getattr(self.instance, 'is_present_address_same_as_permanent', False):
                required_fields.append('permanent_address')
            
            # 4. Other conditional requirements
            if self.instance.civil_status in ['MARRIED', 'SEPARATED', 'WIDOWED', 'DIVORCED', 'LIVE_IN']:
                required_fields.append('spouse_name')
            if self.instance.has_children:
                required_fields.append('num_children')

            if self.instance.current_location == 'AWAY':
                required_fields.extend(['away_duration_years', 'away_duration_months'])
            
            for field_name in required_fields:
                if field_name in self.fields:
                    # Skip permanent_address if same as present is checked
                    if field_name == 'permanent_address' and getattr(self.instance, 'is_present_address_same_as_permanent', False):
                        continue

                    value = getattr(self.instance, field_name, None)
                    # Check for empty strings, None, or empty related objects
                    is_empty = False
                    if not value: # This catches None, empty strings, empty lists, empty FieldFiles
                        is_empty = True
                    elif isinstance(value, str) and not value.strip():
                        is_empty = True
                    elif hasattr(value, 'exists') and not value.exists(): # For QuerySets
                        is_empty = True
                    
                    # Special check for ImageField/FileField
                    if field_name == 'photo' and hasattr(value, 'url'):
                        try:
                            if not value.name:
                                is_empty = True
                        except:
                            is_empty = True

                    if is_empty:
                        # Add highlight class and title
                        existing_classes = self.fields[field_name].widget.attrs.get('class', '')
                        if 'is-invalid-highlight' not in existing_classes:
                            self.fields[field_name].widget.attrs['class'] = f"{existing_classes} is-invalid-highlight".strip()
                        self.fields[field_name].widget.attrs['title'] = "Need to fill up"
                        self.fields[field_name].help_text = "This field needs to be filled up to complete your profile."

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        dob = cleaned_data.get('date_of_birth')

        if first_name and last_name and dob:
            # Strict duplicate check for official's form
            queryset = Resident.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                date_of_birth=dob
            )
            
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                existing = queryset.first()
                raise forms.ValidationError(
                    f"A resident with this name and date of birth already exists in {existing.barangay.name if existing.barangay else 'the system'}."
                )

        household = cleaned_data.get('household')
        new_hh_num = cleaned_data.get('new_household_number')
        new_hh_addr = cleaned_data.get('new_household_address')

        if not household and new_hh_num:
            if not new_hh_addr:
                self.add_error('new_household_address', "Address is required when creating a new household.")
            
            if Household.objects.filter(household_number=new_hh_num).exists():
                self.add_error('new_household_number', f"Household number {new_hh_num} already exists. Please select it from the dropdown.")
        
        if cleaned_data.get('has_children'):
            num_children = cleaned_data.get('num_children')
            if not num_children or num_children <= 0:
                self.add_error('num_children', "Please specify the number of children.")
        
        return cleaned_data

class HouseholdForm(forms.ModelForm):
    latitude = forms.FloatField(required=False, min_value=-90, max_value=90, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}))
    longitude = forms.FloatField(required=False, min_value=-180, max_value=180, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}))

    class Meta:
        model = Household
        fields = ['household_number', 'address', 'barangay', 'latitude', 'longitude']
        widgets = {
            'household_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'barangay': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.location:
            self.fields['latitude'].initial = self.instance.location.y
            self.fields['longitude'].initial = self.instance.location.x

    def clean(self):
        cleaned = super().clean()
        lat = cleaned.get('latitude')
        lng = cleaned.get('longitude')
        if (lat is None) != (lng is None):
            raise forms.ValidationError("Please provide both latitude and longitude, or leave both empty.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        lat = self.cleaned_data.get('latitude')
        lng = self.cleaned_data.get('longitude')
        if lat is not None and lng is not None:
            instance.location = Point(float(lng), float(lat), srid=4326)
        if commit:
            instance.save()
        return instance

class StaffAccountForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return confirm_password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'BARANGAY_STAFF'
        user.is_approved = True
        if commit:
            user.save()
        return user
