from django.urls import path
from . import views

app_name = 'barangay_services'

urlpatterns = [
    path('documents/', views.issue_document_list, name='issued_document_list'),
    path('documents/issue/<int:resident_id>/', views.issue_document, name='issue_document'),
    path('documents/print/<int:doc_id>/', views.print_document, name='print_document'),
    path('receipts/print/<int:receipt_id>/', views.print_receipt, name='print_receipt'),
    path('logs/', views.transaction_logs, name='transaction_logs'),
]
