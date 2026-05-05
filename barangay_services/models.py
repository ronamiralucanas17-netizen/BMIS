from django.db import models
from django.conf import settings
from residents.models import Resident, Barangay

class DocumentType(models.TextChoices):
    BUSINESS_CLEARANCE = 'BUSINESS_CLEARANCE', 'Business Clearance'
    RESIDENTS_CLEARANCE = 'RESIDENTS_CLEARANCE', 'Residents Clearance'
    CERTIFICATE_INDIGENCY = 'CERTIFICATE_INDIGENCY', 'Certificate of Indigency'
    RESIDENTS_ID = 'RESIDENTS_ID', 'Residents ID'

class IssuedDocument(models.Model):
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name='issued_documents')
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50, choices=DocumentType.choices)
    document_number = models.CharField(max_length=50, unique=True)
    purpose = models.TextField(blank=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.get_document_type_display()} - {self.document_number}"

class Receipt(models.Model):
    issued_document = models.OneToOneField(IssuedDocument, on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Receipt {self.receipt_number} for {self.issued_document.document_number}"

class TransactionLog(models.Model):
    ACTION_CHOICES = (
        ('CREATE', 'Created'),
        ('UPDATE', 'Updated'),
        ('DELETE', 'Deleted'),
        ('ISSUE', 'Issued'),
        ('PAY', 'Payment Received'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.action} - {self.model_name} at {self.timestamp}"
