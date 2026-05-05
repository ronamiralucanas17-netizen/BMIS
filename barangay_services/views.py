from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import IssuedDocument, Receipt, TransactionLog, DocumentType
from residents.models import Resident
from users.decorators import staff_only, barangay_admin_only
import uuid

def log_transaction(user, action, model_name, object_id, details, request):
    """Helper to log transactions with IP address."""
    TransactionLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=object_id,
        details=details,
        ip_address=request.META.get('REMOTE_ADDR')
    )

@login_required
@staff_only
def issue_document_list(request):
    """List of documents issued by the barangay."""
    documents = IssuedDocument.objects.all().order_by('-issued_at')
    if request.user.is_barangay_admin:
        # Assuming there's a link to a barangay model or name in user
        # In this project, user has barangay_name
        documents = documents.filter(barangay__name=request.user.barangay_name)
        
    return render(request, 'barangay_services/issued_document_list.html', {'documents': documents})

@login_required
@staff_only
def issue_document(request, resident_id):
    """View to issue a new document to a resident."""
    resident = get_object_or_404(Resident, pk=resident_id)
    
    if request.method == 'POST':
        doc_type = request.POST.get('document_type')
        purpose = request.POST.get('purpose')
        amount = request.POST.get('amount', 0)
        
        # Create IssuedDocument
        doc = IssuedDocument.objects.create(
            resident=resident,
            barangay=resident.barangay,
            document_type=doc_type,
            document_number=f"DOC-{uuid.uuid4().hex[:8].upper()}",
            purpose=purpose,
            issued_by=request.user
        )
        
        # Create Receipt if amount > 0
        if float(amount) > 0:
            Receipt.objects.create(
                issued_document=doc,
                receipt_number=f"OR-{uuid.uuid4().hex[:8].upper()}",
                amount=amount,
                total_amount=amount,
                processed_by=request.user
            )
            doc.is_paid = True
            doc.save()
            
        # Log Transaction
        log_transaction(
            request.user, 'ISSUE', 'IssuedDocument', doc.id,
            f"Issued {doc.get_document_type_display()} to {resident.full_name}",
            request
        )
        
        messages.success(request, f"{doc.get_document_type_display()} issued successfully.")
        return redirect('barangay_services:issued_document_list')
        
    return render(request, 'barangay_services/issue_document_form.html', {
        'resident': resident,
        'doc_types': DocumentType.choices
    })

@login_required
@staff_only
def transaction_logs(request):
    """View to see all transaction logs."""
    logs = TransactionLog.objects.all().order_by('-timestamp')
    if request.user.is_barangay_admin:
        # Filter logs related to their barangay if possible
        pass
    return render(request, 'barangay_services/transaction_logs.html', {'logs': logs})

@login_required
def print_document(request, doc_id):
    """Simulate document printing."""
    doc = get_object_or_404(IssuedDocument, pk=doc_id)
    # In a real app, you'd use a PDF library like WeasyPrint or reportlab
    return render(request, 'barangay_services/document_template.html', {'doc': doc})

@login_required
def print_receipt(request, receipt_id):
    """Simulate receipt printing."""
    receipt = get_object_or_404(Receipt, pk=receipt_id)
    return render(request, 'barangay_services/receipt_template.html', {'receipt': receipt})
