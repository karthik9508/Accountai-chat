from django import forms

from .models import BusinessProfile, Category, Customer, Transaction, Invoice, InvoiceItem


def apply_input_classes(field):
    widget = field.widget
    if isinstance(widget, forms.CheckboxInput):
        return

    existing_class = widget.attrs.get('class', '')
    widget.attrs['class'] = f'{existing_class} form-control'.strip()
    if isinstance(widget, forms.DateInput):
        widget.attrs.setdefault('type', 'date')


class SignupForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'class': 'form-control'}),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
    )


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autocomplete': 'email', 'class': 'form-control'}),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'class': 'form-control'}),
    )


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            apply_input_classes(field)


class BusinessProfileForm(StyledModelForm):
    class Meta:
        model = BusinessProfile
        fields = ['name', 'base_currency', 'timezone', 'address', 'contact_number', 'tax_id']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'e.g. 123 Business Rd, Suite 100\nCity, State 12345'}),
            'name': forms.TextInput(attrs={'placeholder': 'Your Business Name'}),
            'contact_number': forms.TextInput(attrs={'placeholder': '+1 (555) 000-0000'}),
            'tax_id': forms.TextInput(attrs={'placeholder': 'e.g. GSTIN123456789'}),
        }


class TransactionForm(StyledModelForm):
    class Meta:
        model = Transaction
        fields = ['kind', 'amount', 'currency', 'occurred_on', 'category', 'counterparty', 'note', 'status']
        widgets = {
            'occurred_on': forms.DateInput(attrs={'type': 'date'}),
            'note': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.business = business
        self.fields['currency'].initial = 'INR'
        self.fields['category'].required = False
        if business is not None:
            self.fields['currency'].initial = business.base_currency
            self.fields['category'].queryset = business.categories.order_by('kind', 'name')

    def clean_category(self):
        category = self.cleaned_data.get('category')
        if category and self.business and category.business_id != self.business.id:
            raise forms.ValidationError('Choose a category from your business only.')
        return category

    def clean(self):
        cleaned_data = super().clean()
        kind = cleaned_data.get('kind')
        category = cleaned_data.get('category')
        if category and kind and category.kind != kind:
            self.add_error('category', 'Category type must match the transaction type.')
        return cleaned_data


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ['name', 'kind']

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.business = business

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        kind = cleaned_data.get('kind')
        if name and kind and self.business:
            exists = Category.objects.filter(
                business=self.business,
                name__iexact=name,
                kind=kind,
            ).exists()
            if exists:
                self.add_error('name', 'A category with this name and type already exists.')
        return cleaned_data


class CustomerForm(StyledModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.business = business

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        email = cleaned_data.get('email') or ''
        if name and self.business:
            exists = Customer.objects.filter(
                business=self.business,
                name__iexact=name,
                email__iexact=email,
            ).exists()
            if exists:
                self.add_error('name', 'A customer with this name and email already exists.')
        return cleaned_data


class InvoiceForm(StyledModelForm):
    class Meta:
        model = Invoice
        fields = ['customer', 'invoice_number', 'status', 'issue_date', 'due_date', 'currency', 'notes']
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.business = business
        if business is not None:
            self.fields['currency'].initial = business.base_currency
            self.fields['customer'].queryset = business.customers.order_by('name')


class InvoiceItemForm(StyledModelForm):
    class Meta:
        model = InvoiceItem
        fields = ['description', 'quantity', 'unit_price']

InvoiceItemFormSet = forms.inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True
)
