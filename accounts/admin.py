from django.contrib import admin

from .models import BusinessProfile, Category, ChatMessage, Customer, Invoice, Transaction


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_email', 'base_currency', 'timezone', 'is_active')
    list_filter = ('is_active', 'base_currency', 'timezone')
    search_fields = ('name', 'owner_email')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'kind', 'business', 'is_system_default')
    list_filter = ('kind', 'is_system_default')
    search_fields = ('name',)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'business', 'email', 'phone')
    list_filter = ('business',)
    search_fields = ('name', 'email', 'phone')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('kind', 'amount', 'currency', 'business', 'category', 'occurred_on', 'status')
    list_filter = ('kind', 'currency', 'status', 'occurred_on')
    search_fields = ('counterparty', 'note', 'source_message')
    date_hierarchy = 'occurred_on'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'business', 'customer', 'status', 'issue_date', 'due_date', 'total_amount')
    list_filter = ('status', 'currency', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'customer__name', 'notes')
    date_hierarchy = 'issue_date'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('business', 'role', 'processing_status', 'created_at')
    list_filter = ('role', 'processing_status')
    search_fields = ('message_text',)
