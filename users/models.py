from django.db import models
from django.db.utils import ProgrammingError
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'System Admin (DILG)'),
        ('BARANGAY', 'Barangay Admin'),
        ('BARANGAY_STAFF', 'Barangay Staff'),
        ('RESIDENT', 'Resident'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='RESIDENT')
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False) # For Barangay approval
    data_privacy_consent = models.BooleanField(default=False)
    
    # Linked Barangay (for BARANGAY and RESIDENT roles)
    barangay_name = models.CharField(max_length=100, blank=True, null=True)

    @property
    def is_system_admin(self):
        return self.role == 'ADMIN' or self.is_superuser

    @property
    def is_barangay_admin(self):
        return self.role == 'BARANGAY'

    @property
    def is_barangay_staff(self):
        return self.role == 'BARANGAY_STAFF'

    @property
    def is_any_barangay_official(self):
        return self.role in ['BARANGAY', 'BARANGAY_STAFF']

    @property
    def is_resident(self):
        return self.role == 'RESIDENT'

    def unread_notifications_count(self):
        try:
            return self.notifications.filter(is_read=False).count()
        except (ProgrammingError, AttributeError):
            return 0

    @property
    def pending_residents_count(self):
        if self.is_any_barangay_official:
            from residents.models import Resident, Barangay
            try:
                if self.is_barangay_admin:
                    brgy = getattr(self, 'managed_barangay', None)
                    if not brgy:
                        brgy = Barangay.objects.filter(name=self.barangay_name).first()
                else:
                    brgy = Barangay.objects.filter(name=self.barangay_name).first()
                
                if brgy:
                    return Resident.objects.filter(barangay=brgy, profile_status='PENDING_APPROVAL').count()
            except:
                pass
        return 0

    @property
    def pending_reports_count(self):
        if self.is_any_barangay_official:
            from residents.models import IncidentReport, Barangay
            try:
                brgy = Barangay.objects.filter(name=self.barangay_name).first()
                if brgy:
                    return IncidentReport.objects.filter(barangay=brgy, status='PENDING').count()
            except:
                pass
        return 0

    @property
    def pending_service_requests_count(self):
        if self.is_any_barangay_official:
            from residents.models import ServiceRequest, Barangay
            try:
                brgy = Barangay.objects.filter(name=self.barangay_name).first()
                if brgy:
                    return ServiceRequest.objects.filter(barangay=brgy, status='PENDING').count()
            except:
                pass
        return 0
