from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BusinessProfile(TimeStampedModel):
    name = models.CharField(max_length=255)
    owner_email = models.EmailField(db_index=True)
    base_currency = models.CharField(max_length=3, default='INR')
    timezone = models.CharField(max_length=64, default='Asia/Kolkata')
    is_active = models.BooleanField(default=True)
    
    # Business Details
    address = models.TextField(blank=True, null=True, help_text="Physical or operating address")
    contact_number = models.CharField(max_length=50, blank=True, null=True, help_text="Primary support or business phone number")
    tax_id = models.CharField(max_length=100, blank=True, null=True, help_text="GST, VAT, EIN, or equivalent tax registration number")

    class Meta:
        ordering = ['name']
        verbose_name = 'Business profile'
        verbose_name_plural = 'Business profiles'

    def __str__(self):
        return self.name


class Category(TimeStampedModel):
    EXPENSE = 'expense'
    INCOME = 'income'
    CATEGORY_KIND_CHOICES = [
        (EXPENSE, 'Expense'),
        (INCOME, 'Income'),
    ]

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name='categories',
        blank=True,
        null=True,
        help_text='Leave empty for shared default categories.',
    )
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=CATEGORY_KIND_CHOICES)
    is_system_default = models.BooleanField(default=False)

    class Meta:
        ordering = ['kind', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['business', 'name', 'kind'],
                name='unique_category_per_business_and_kind',
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.kind})'


class Customer(TimeStampedModel):
    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name='customers',
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['business', 'name', 'email'],
                name='unique_customer_per_business',
            )
        ]

    def __str__(self):
        return self.name


class Transaction(TimeStampedModel):
    DRAFT = 'draft'
    CONFIRMED = 'confirmed'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (CONFIRMED, 'Confirmed'),
    ]

    EXPENSE = 'expense'
    INCOME = 'income'
    TRANSACTION_KIND_CHOICES = [
        (EXPENSE, 'Expense'),
        (INCOME, 'Income'),
    ]

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    kind = models.CharField(max_length=10, choices=TRANSACTION_KIND_CHOICES)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    currency = models.CharField(max_length=3, default='INR')
    occurred_on = models.DateField()
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='transactions',
        blank=True,
        null=True,
    )
    counterparty = models.CharField(max_length=255, blank=True)
    note = models.TextField(blank=True)
    source_message = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=DRAFT)

    class Meta:
        ordering = ['-occurred_on', '-created_at']

    def __str__(self):
        return f'{self.get_kind_display()} {self.amount} {self.currency}'


class Invoice(TimeStampedModel):
    DRAFT = 'draft'
    SENT = 'sent'
    PAID = 'paid'
    OVERDUE = 'overdue'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (SENT, 'Sent'),
        (PAID, 'Paid'),
        (OVERDUE, 'Overdue'),
        (CANCELLED, 'Cancelled'),
    ]

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name='invoices',
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='invoices',
    )
    invoice_number = models.CharField(max_length=50)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=DRAFT)
    issue_date = models.DateField()
    due_date = models.DateField()
    currency = models.CharField(max_length=3, default='INR')
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-issue_date', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['business', 'invoice_number'],
                name='unique_invoice_number_per_business',
            )
        ]

    def __str__(self):
        return self.invoice_number


class InvoiceItem(TimeStampedModel):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items'
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.description} ({self.quantity} x {self.unit_price})"


class ChatMessage(TimeStampedModel):
    USER = 'user'
    ASSISTANT = 'assistant'
    SYSTEM = 'system'
    ROLE_CHOICES = [
        (USER, 'User'),
        (ASSISTANT, 'Assistant'),
        (SYSTEM, 'System'),
    ]

    PENDING = 'pending'
    PROCESSED = 'processed'
    CONFIRMED = 'confirmed'
    FAILED = 'failed'
    PROCESSING_STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSED, 'Processed'),
        (CONFIRMED, 'Confirmed'),
        (FAILED, 'Failed'),
    ]

    business = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=USER)
    message_text = models.TextField()
    parsed_payload = models.JSONField(blank=True, null=True)
    processing_status = models.CharField(
        max_length=12,
        choices=PROCESSING_STATUS_CHOICES,
        default=PENDING,
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.role}: {self.message_text[:40]}'
