from django.db import models
from django.contrib.gis.db import models as gis_models
from django.conf import settings
import threading
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

class Barangay(models.Model):
    name = models.CharField(max_length=100, unique=True)
    municipality = models.CharField(max_length=100, default='Ormoc City')
    email = models.EmailField(unique=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    captain_name = models.CharField(max_length=100)
    admin_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='managed_barangay',
        blank=True,
        null=True,
    )
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    boundary = gis_models.PolygonField(srid=4326, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name}, {self.municipality}"

    def save(self, *args, **kwargs):
        # Sync is_active with the admin user
        if self.admin_user and self.admin_user.is_active != self.is_active:
            self.admin_user.is_active = self.is_active
            self.admin_user.save(update_fields=['is_active'])
        super().save(*args, **kwargs)

class Household(models.Model):
    household_number = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    location = gis_models.PointField(srid=4326, blank=True, null=True)
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name='households')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"HH {self.household_number} - {self.barangay.name}"

class Official(models.Model):
    POSITIONS = (
        ('CAPTAIN', 'Barangay Captain'),
        ('KAGAWAD', 'Barangay Kagawad'),
        ('SK_CHAIRMAN', 'SK Chairman'),
        ('SK_KAGAWAD', 'SK Kagawad'),
        ('SECRETARY', 'Secretary'),
        ('TREASURER', 'Treasurer'),
    )
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name='officials', null=True, blank=True)
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=50, choices=POSITIONS)
    term_start = models.DateField()
    term_end = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_position_display()})"

class Service(models.Model):
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name='available_services')
    name = models.CharField(max_length=100)
    description = models.TextField()
    requirements = models.TextField()
    processing_time = models.CharField(max_length=100) # e.g. "1-2 working days"
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.barangay.name}"

class ServiceRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed'),
    )

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='requests')
    resident = models.ForeignKey('Resident', on_delete=models.CASCADE, related_name='service_requests')
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name='service_requests')
    request_message = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.service.name} - {self.resident.full_name} ({self.status})"

class Resident(models.Model):
    GENDER_CHOICES = (
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    )
    CIVIL_STATUS_CHOICES = (
        ('SINGLE', 'Single'),
        ('MARRIED', 'Married'),
        ('WIDOWED', 'Widowed'),
        ('SEPARATED', 'Separated'),
        ('DIVORCED', 'Divorced'),
        ('LIVE_IN', 'Live-in'),
    )
    EDUCATION_CHOICES = (
        ('NONE', 'No Formal Education'),
        ('ELEMENTARY_UNDERGRAD', 'Elementary Undergraduate'),
        ('ELEMENTARY_GRAD', 'Elementary Graduate'),
        ('HIGHSCHOOL_UNDERGRAD', 'High School Undergraduate'),
        ('HIGHSCHOOL_GRAD', 'High School Graduate'),
        ('VOCATIONAL', 'Vocational Course'),
        ('COLLEGE_UNDERGRAD', 'College Undergraduate'),
        ('COLLEGE_GRAD', 'College Graduate'),
        ('POST_GRAD', 'Post Graduate'),
    )
    RESIDENCY_STATUS_CHOICES = (
        ('PERMANENT', 'Permanent'),
        ('TRANSIENT', 'Transient'),
    )
    PROFILE_STATUS_CHOICES = (
        ('INCOMPLETE', 'Incomplete'),
        ('PENDING_APPROVAL', 'Pending Approval'),
        ('APPROVED', 'Approved'),
    )
    EMPLOYMENT_STATUS_CHOICES = (
        ('EMPLOYED', 'Employed'),
        ('UNEMPLOYED', 'Unemployed'),
        ('RETIRED', 'Retired'),
        ('SELF_EMPLOYED', 'Self-employed'),
        ('OFW', 'OFW'),
        ('OTHER', 'Other'),
    )
    AGE_RANGE_CHOICES = (
        ('INFANT', 'Infant (0-1)'),
        ('CHILDHOOD', 'Childhood (2-12)'),
        ('ADOLESCENCE', 'Adolescence (13-17)'),
        ('YOUNG_ADULTHOOD', 'Young Adulthood (18-30)'),
        ('ADULTHOOD', 'Adulthood (31-45)'),
        ('MIDDLE_AGE', 'Middle Age (46-59)'),
        ('OLD_AGE', 'Old Age (60-74)'),
        ('SENIOR_CITIZEN', 'Senior Citizen (75+)'),
    )

    RESIDENCY_TYPE_CHOICES = (
        ('HOUSE_OWNER', 'House Owner'),
        ('BOARDER', 'Boarder'),
        ('TRANSIENT', 'Transient'),
    )

    CURRENT_LOCATION_CHOICES = (
        ('IN_BARANGAY', 'Currently living in the barangay'),
        ('AWAY', 'Currently away from home'),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='resident_profile')
    photo = models.ImageField(upload_to='resident_photos/', blank=True, null=True)
    resident_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    birthplace = models.CharField(max_length=255, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    civil_status = models.CharField(max_length=20, choices=CIVIL_STATUS_CHOICES, blank=True)
    spouse_name = models.CharField(max_length=255, blank=True, null=True)
    citizenship = models.CharField(max_length=100, default='Filipino')
    religion = models.CharField(max_length=100, blank=True, null=True)
    
    # Family information
    has_children = models.BooleanField(default=False)
    num_children = models.PositiveIntegerField(default=0)
    children_details = models.TextField(blank=True, null=True, help_text="Names and ages of children, especially those of legal age.")
    father = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children_from_father')
    mother = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children_from_mother')
    father_name = models.CharField(max_length=255, blank=True, null=True) # For non-registered parents
    is_father_deceased = models.BooleanField(default=False)
    mother_name = models.CharField(max_length=255, blank=True, null=True) # For non-registered parents
    mother_maiden_name = models.CharField(max_length=255, blank=True, null=True)
    is_mother_deceased = models.BooleanField(default=False)
    
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name='residents', null=True, blank=True)
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='members', null=True, blank=True)
    zone_street_purok = models.CharField(max_length=255, blank=True, null=True)
    
    # Address details
    present_address = models.CharField(max_length=255, blank=True, null=True)
    permanent_address = models.CharField(max_length=255, blank=True, null=True)
    is_present_address_same_as_permanent = models.BooleanField(default=True)
    residency_type = models.CharField(max_length=20, choices=RESIDENCY_TYPE_CHOICES, default='HOUSE_OWNER')
    years_in_barangay = models.PositiveIntegerField(default=0)
    
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    educational_attainment = models.CharField(max_length=100, choices=EDUCATION_CHOICES, blank=True)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, blank=True)
    employment_status_other = models.CharField(max_length=100, blank=True, null=True)
    employment_history = models.TextField(blank=True, null=True)
    
    is_student = models.BooleanField(default=False)
    student_level = models.CharField(max_length=20, choices=(
        ('ELEMENTARY', 'Elementary'),
        ('HIGHSCHOOL', 'High School'),
        ('COLLEGE', 'College'),
    ), blank=True, null=True)
    elementary_school = models.CharField(max_length=255, blank=True, null=True)
    high_school = models.CharField(max_length=255, blank=True, null=True)
    college = models.CharField(max_length=255, blank=True, null=True)
    elementary_graduated_at = models.CharField(max_length=255, blank=True, null=True, help_text="School where elementary was completed")
    high_school_graduated_at = models.CharField(max_length=255, blank=True, null=True, help_text="School where high school was completed")
    
    is_voter = models.BooleanField(default=False)
    residency_status = models.CharField(max_length=50, choices=RESIDENCY_STATUS_CHOICES, blank=True)
    current_location = models.CharField(max_length=20, choices=CURRENT_LOCATION_CHOICES, blank=True, null=True)
    away_duration_years = models.PositiveSmallIntegerField(default=0)
    away_duration_months = models.PositiveSmallIntegerField(default=0)
    profile_status = models.CharField(max_length=20, choices=PROFILE_STATUS_CHOICES, default='INCOMPLETE')
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    age_range = models.CharField(max_length=20, choices=AGE_RANGE_CHOICES, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.resident_code:
            import uuid
            self.resident_code = f"RES-{uuid.uuid4().hex[:8].upper()}"
        
        self.age_range = self.computed_age_range
        
        # Automatic profile status update
        if self.has_completed_profile():
            if self.profile_status == 'INCOMPLETE':
                self.profile_status = 'PENDING_APPROVAL'
        else:
            if self.profile_status != 'INCOMPLETE':
                # If it was previously PENDING_APPROVAL or even APPROVED, 
                # but now it's missing required fields, mark it as INCOMPLETE again.
                # This helps when new required fields are added.
                self.profile_status = 'INCOMPLETE'
        
        # Automatic parent detection based on name and household/barangay
        if not self.father and self.father_name:
            # Try to find father in the same household or barangay
            # If child is legal age (18+), they might be in a different household but same barangay
            parent_query = models.Q(last_name=self.last_name, gender='MALE')
            if self.household:
                parent_query |= models.Q(household=self.household)
            
            father_match = Resident.objects.filter(
                models.Q(barangay=self.barangay),
                parent_query
            ).filter(
                models.Q(first_name__icontains=self.father_name.split()[0])
            ).first()
            if father_match:
                self.father = father_match

        if not self.mother and (self.mother_name or self.mother_maiden_name):
            # Try to find mother in the same household or barangay
            parent_query = models.Q(gender='FEMALE')
            if self.household:
                parent_query |= models.Q(household=self.household)

            search_name = self.mother_name or self.mother_maiden_name
            mother_match = Resident.objects.filter(
                models.Q(barangay=self.barangay),
                parent_query
            ).filter(
                models.Q(first_name__icontains=search_name.split()[0])
            ).first()
            if mother_match:
                self.mother = mother_match
            
        # Ensure barangay matches household's barangay
        if self.household and self.household.barangay:
            self.barangay = self.household.barangay
        
        # Sync is_active with the associated User
        if self.user and self.user.is_active != self.is_active:
            self.user.is_active = self.is_active
            self.user.save(update_fields=['is_active'])
            
        super().save(*args, **kwargs)

    @property
    def is_minor(self):
        if not self.date_of_birth:
            return False
        from datetime import date
        today = date.today()
        age = today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return age < 18

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        age = today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return age if age >= 0 else None

    @property
    def computed_age_range(self):
        age = self.age
        if age is None:
            return None
        if age <= 1:
            return 'INFANT'
        if age <= 12:
            return 'CHILDHOOD'
        if age <= 17:
            return 'ADOLESCENCE'
        if age <= 30:
            return 'YOUNG_ADULTHOOD'
        if age <= 45:
            return 'ADULTHOOD'
        if age <= 59:
            return 'MIDDLE_AGE'
        if age <= 74:
            return 'OLD_AGE'
        return 'SENIOR_CITIZEN'

    @property
    def computed_age_range_display(self):
        if not self.computed_age_range:
            return ''
        label_map = dict(self.AGE_RANGE_CHOICES)
        return label_map.get(self.computed_age_range, self.computed_age_range)

    @property
    def is_baby(self):
        return self.age_range == 'INFANT'

    @property
    def is_senior(self):
        return self.age_range in ['OLD_AGE', 'SENIOR_CITIZEN']

    def has_completed_profile(self):
        """
        Check if all essential fields are filled.
        This should match the required_fields logic in forms.py
        """
        # 1. Base required fields for everyone
        required_fields = [
            'photo', 'first_name', 'last_name', 'date_of_birth', 'gender', 
            'civil_status', 'residency_status', 'present_address', 
            'residency_type', 'contact_number', 'household_id', 
            'birthplace', 'citizenship', 'religion', 'years_in_barangay', 
            'father_name', 'mother_maiden_name', 'zone_street_purok',
            'current_location',
        ]
        
        # 2. Conditional: If NOT a student, these are required
        if not self.is_student:
            required_fields.extend([
                'educational_attainment', 'occupation', 'income', 'employment_status'
            ])
        
        # 3. Check all required fields so far
        for field in required_fields:
            # Special handling for permanent_address if same as present
            if field == 'permanent_address' and self.is_present_address_same_as_permanent:
                if not self.present_address or not self.present_address.strip():
                    return False
                continue

            val = getattr(self, field, None)
            if not val:
                return False
            if isinstance(val, str) and not val.strip():
                return False
            # Check for related objects (e.g., household_id)
            if field.endswith('_id') and not val:
                return False
                
        # 4. Additional Conditional requirements
        # Permanent address (if not same as present)
        if not self.is_present_address_same_as_permanent:
            if not self.permanent_address or not self.permanent_address.strip():
                return False

        # Spouse name if married/etc
        if self.civil_status in ['MARRIED', 'SEPARATED', 'WIDOWED', 'DIVORCED', 'LIVE_IN']:
            if not self.spouse_name or not self.spouse_name.strip():
                return False

        # Children count if has_children
        if self.has_children and (self.num_children is None or self.num_children < 0):
            return False

        # Student details if is_student
        if self.is_student:
            if not self.student_level:
                return False
            
            level = self.student_level.upper()
            if level == 'ELEMENTARY' and not self.elementary_school:
                return False
            if (level == 'HIGHSCHOOL' or level == 'HIGH SCHOOL') and not self.high_school:
                return False
            if level == 'COLLEGE' and not self.college:
                return False

        if self.current_location == 'AWAY':
            if (self.away_duration_years or 0) <= 0 and (self.away_duration_months or 0) <= 0:
                return False

        return True

    @property
    def full_name(self):
        return f"{self.first_name} {self.middle_name if self.middle_name else ''} {self.last_name}"

    def __str__(self):
        return self.full_name

class IncidentReport(models.Model):
    REPORT_TYPES = (
        ('COMPLAINT', 'Complaint'),
        ('INCIDENT', 'Incident'),
        ('REQUEST', 'Request'),
    )
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('IN_REVIEW', 'In Review'),
        ('SCHEDULED', 'Scheduled'),
        ('RESOLVED', 'Resolved'),
    )
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='reports', null=True, blank=True)
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name='reports', null=True, blank=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    respondent_name = models.CharField(max_length=100, blank=True, null=True) # Person being reported
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # GIS Location for Incident
    location_point = gis_models.PointField(srid=4326, blank=True, null=True)
    location_address = models.CharField(max_length=255, blank=True, null=True)
    
    # Scheduling for Summons
    schedule_date = models.DateField(blank=True, null=True)
    schedule_time = models.TimeField(blank=True, null=True)
    location = models.CharField(max_length=200, default='Barangay Hall')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

class Announcement(models.Model):
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name='announcements', null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements_created')
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_global = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True, help_text="When the announcement becomes visible")
    end_date = models.DateField(null=True, blank=True, help_text="When the announcement disappears")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def is_active(self):
        from django.utils import timezone
        today = timezone.now().date()
        if self.start_date and self.start_date > today:
            return False
        if self.end_date and self.end_date < today:
            return False
        return True

def resident_document_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/resident_docs/<user_id>/<filename>
    return f'resident_docs/{instance.resident.user.id}/{filename}'

class ResidentDocument(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to=resident_document_path)
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.resident.full_name} - {self.description}"


_audit_ctx = threading.local()


def set_audit_context(user=None, request=None):
    _audit_ctx.user = user
    _audit_ctx.request = request


def clear_audit_context():
    _audit_ctx.user = None
    _audit_ctx.request = None


def get_audit_user():
    return getattr(_audit_ctx, 'user', None)


def get_audit_request():
    return getattr(_audit_ctx, 'request', None)


def _get_barangay_for_user(user):
    if not user:
        return None
    if getattr(user, 'is_barangay_admin', False):
        brgy = getattr(user, 'managed_barangay', None)
        if brgy:
            return brgy
        name = getattr(user, 'barangay_name', None)
        if name:
            return Barangay.objects.filter(name=name).first()
        return None
    if getattr(user, 'is_barangay_staff', False):
        name = getattr(user, 'barangay_name', None)
        if name:
            return Barangay.objects.filter(name=name).first()
        return None
    if getattr(user, 'is_resident', False):
        try:
            r = user.resident_profile
        except Exception:
            return None
        if getattr(r, 'barangay', None):
            return r.barangay
        try:
            if r.household and r.household.barangay:
                return r.household.barangay
        except Exception:
            return None
    return None


class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('REQUEST', 'Request'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')
    actor_role = models.CharField(max_length=20, blank=True)
    barangay = models.ForeignKey(Barangay, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)

    path = models.TextField(blank=True)
    method = models.CharField(max_length=10, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at'], name='res_audit_created_at_idx'),
            models.Index(fields=['barangay', '-created_at'], name='res_audit_brgy_created_idx'),
            models.Index(fields=['actor', '-created_at'], name='res_audit_actor_created_idx'),
            models.Index(fields=['action', '-created_at'], name='res_audit_action_created_idx'),
        ]

    def __str__(self):
        who = self.actor.username if self.actor else 'Unknown'
        return f"{self.created_at} {who} {self.action} {self.object_type} {self.object_id}".strip()


def _audit_object_ref(instance):
    obj_type = f"{instance._meta.app_label}.{instance.__class__.__name__}"
    obj_id = str(getattr(instance, 'pk', '') or '')
    try:
        obj_repr = str(instance)
    except Exception:
        obj_repr = obj_type
    return obj_type, obj_id, obj_repr[:255]


def _audit_guess_barangay(actor, instance):
    if actor:
        b = _get_barangay_for_user(actor)
        if b:
            return b
    if isinstance(instance, Barangay):
        return instance
    if hasattr(instance, 'barangay') and getattr(instance, 'barangay', None):
        return getattr(instance, 'barangay', None)
    return None


def _audit_safe_field_value(field, obj):
    if isinstance(field, models.ForeignKey):
        return getattr(obj, field.attname, None)
    if isinstance(field, (gis_models.PointField, gis_models.PolygonField, gis_models.MultiPolygonField)):
        try:
            g = getattr(obj, field.name, None)
            return g.wkt if g else None
        except Exception:
            return None
    value = getattr(obj, field.name, None)
    if isinstance(value, (list, dict, int, float, bool)) or value is None:
        return value
    return str(value)


def _audit_changes(old, new):
    changes = {}
    for field in new._meta.fields:
        name = field.name
        if name in ('id', 'password', 'last_login'):
            continue
        try:
            before = _audit_safe_field_value(field, old)
            after = _audit_safe_field_value(field, new)
        except Exception:
            continue
        if before != after:
            changes[name] = {'from': before, 'to': after}
    return changes


_AUDIT_TRACKED_MODELS = (
    Barangay,
    Household,
    Resident,
    Official,
    Service,
    ServiceRequest,
    IncidentReport,
    Announcement,
)


@receiver(pre_save, dispatch_uid='auditlog_pre_save_capture')
def _audit_pre_save(sender, instance, **kwargs):
    if sender not in _AUDIT_TRACKED_MODELS:
        return
    if not getattr(instance, 'pk', None):
        return
    try:
        instance._audit_old_instance = sender.objects.get(pk=instance.pk)
    except Exception:
        instance._audit_old_instance = None


@receiver(post_save, dispatch_uid='auditlog_post_save_write')
def _audit_post_save(sender, instance, created, **kwargs):
    if sender not in _AUDIT_TRACKED_MODELS:
        return
    actor = get_audit_user()
    req = get_audit_request()
    action = 'CREATE' if created else 'UPDATE'
    obj_type, obj_id, obj_repr = _audit_object_ref(instance)
    barangay = _audit_guess_barangay(actor, instance)
    details = {}
    if req is not None:
        details['path'] = getattr(req, 'path', '')
    if not created:
        old = getattr(instance, '_audit_old_instance', None)
        if old is not None:
            details['changes'] = _audit_changes(old, instance)
    try:
        AuditLog.objects.create(
            actor=actor,
            actor_role=getattr(actor, 'role', '') if actor else '',
            barangay=barangay,
            action=action,
            object_type=obj_type,
            object_id=obj_id,
            object_repr=obj_repr,
            path=getattr(req, 'path', '') if req else '',
            method=getattr(req, 'method', '') if req else '',
            ip_address=(req.META.get('REMOTE_ADDR') if req else None),
            user_agent=(req.META.get('HTTP_USER_AGENT', '')[:1000] if req else ''),
            details=details,
        )
    except Exception:
        pass


@receiver(post_delete, dispatch_uid='auditlog_post_delete_write')
def _audit_post_delete(sender, instance, **kwargs):
    if sender not in _AUDIT_TRACKED_MODELS:
        return
    actor = get_audit_user()
    req = get_audit_request()
    obj_type, obj_id, obj_repr = _audit_object_ref(instance)
    barangay = _audit_guess_barangay(actor, instance)
    details = {}
    if req is not None:
        details['path'] = getattr(req, 'path', '')
    try:
        AuditLog.objects.create(
            actor=actor,
            actor_role=getattr(actor, 'role', '') if actor else '',
            barangay=barangay,
            action='DELETE',
            object_type=obj_type,
            object_id=obj_id,
            object_repr=obj_repr,
            path=getattr(req, 'path', '') if req else '',
            method=getattr(req, 'method', '') if req else '',
            ip_address=(req.META.get('REMOTE_ADDR') if req else None),
            user_agent=(req.META.get('HTTP_USER_AGENT', '')[:1000] if req else ''),
            details=details,
        )
    except Exception:
        pass
