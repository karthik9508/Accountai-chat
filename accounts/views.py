from django.contrib import messages
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import BusinessProfileForm, CategoryForm, CustomerForm, LoginForm, SignupForm, TransactionForm, InvoiceForm, InvoiceItemFormSet
from .models import Transaction, ChatMessage, Category, Invoice, InvoiceItem
from .services import get_or_create_business_for_email, get_transaction_filters, get_transaction_summary
from .supabase_client import get_supabase_client
from .ai_parser import call_ai_parser


def get_session_user_email(request):
    return request.session.get('supabase_user')


def require_session_user(request):
    user_email = get_session_user_email(request)
    if not user_email:
        messages.info(request, 'Please log in to continue.')
        return None
    return user_email


def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            client = get_supabase_client()
            credentials = {
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password'],
            }
            try:
                auth_response = client.auth.sign_up(credentials)
            except Exception as exc:
                messages.error(request, f'Sign up failed: {exc}')
            else:
                user = getattr(auth_response, 'user', None)
                session = getattr(auth_response, 'session', None)
                request.session['supabase_user'] = user.email if user else form.cleaned_data['email']
                request.session['supabase_session'] = session.access_token if session else ''
                messages.success(request, 'Account created successfully. Please check your email for confirmation if required.')
                return redirect(reverse('accounts:profile'))
    else:
        form = SignupForm()
    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            client = get_supabase_client()
            credentials = {
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password'],
            }
            try:
                auth_response = client.auth.sign_in_with_password(credentials)
            except Exception as exc:
                messages.error(request, f'Login failed: {exc}')
            else:
                user = getattr(auth_response, 'user', None)
                session = getattr(auth_response, 'session', None)
                if user:
                    request.session['supabase_user'] = user.email
                    request.session['supabase_session'] = session.access_token if session else ''
                    messages.success(request, 'Logged in successfully.')
                    return redirect(reverse('accounts:profile'))
                messages.error(request, 'Login failed. Please verify your credentials.')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    request.session.pop('supabase_user', None)
    request.session.pop('supabase_session', None)
    messages.success(request, 'You have been logged out.')
    return redirect(reverse('accounts:login'))


def profile(request):
    user_email = get_session_user_email(request)
    if not user_email:
        messages.info(request, 'Please log in to view your profile.')
        return redirect(reverse('accounts:login'))

    business = get_or_create_business_for_email(user_email)
    
    if request.method == 'POST':
        form = BusinessProfileForm(request.POST, instance=business)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect(reverse('accounts:profile'))
    else:
        form = BusinessProfileForm(instance=business)
        
    summary = get_transaction_summary(business)
    context = {
        'user_email': user_email,
        'business': business,
        'form': form,
        'summary': summary,
        'category_count': business.categories.count(),
        'customer_count': business.customers.count(),
        'invoice_count': business.invoices.count(),
    }
    return render(request, 'accounts/profile.html', context)


def transaction_list(request):
    user_email = require_session_user(request)
    if not user_email:
        return redirect(reverse('accounts:login'))

    business = get_or_create_business_for_email(user_email)
    kind = request.GET.get('kind', '')
    status = request.GET.get('status', '')
    transactions = get_transaction_filters(
        business.transactions.select_related('category').order_by('-occurred_on', '-created_at'),
        kind=kind,
        status=status,
    )
    summary = get_transaction_summary(business)

    return render(
        request,
        'accounts/transaction_list.html',
        {
            'business': business,
            'transactions': transactions,
            'summary': summary,
            'selected_kind': kind,
            'selected_status': status,
            'status_choices': Transaction.STATUS_CHOICES,
            'kind_choices': Transaction.TRANSACTION_KIND_CHOICES,
        },
    )


def transaction_create(request):
    user_email = require_session_user(request)
    if not user_email:
        return redirect(reverse('accounts:login'))

    business = get_or_create_business_for_email(user_email)
    if request.method == 'POST':
        form = TransactionForm(request.POST, business=business)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.business = business
            transaction.save()
            messages.success(request, 'Transaction saved successfully.')
            return redirect(reverse('accounts:transactions'))
    else:
        form = TransactionForm(
            business=business,
            initial={'currency': business.base_currency, 'status': Transaction.CONFIRMED},
        )

    return render(request, 'accounts/transaction_form.html', {'form': form, 'business': business})


def category_list(request):
    user_email = require_session_user(request)
    if not user_email:
        return redirect(reverse('accounts:login'))

    business = get_or_create_business_for_email(user_email)
    if request.method == 'POST':
        form = CategoryForm(request.POST, business=business)
        if form.is_valid():
            category = form.save(commit=False)
            category.business = business
            category.save()
            messages.success(request, 'Category added successfully.')
            return redirect(reverse('accounts:categories'))
    else:
        form = CategoryForm(business=business)

    categories = business.categories.order_by('kind', 'name')
    grouped_counts = categories.values('kind').annotate(total=Count('id')).order_by('kind')
    return render(
        request,
        'accounts/category_list.html',
        {
            'business': business,
            'form': form,
            'categories': categories,
            'grouped_counts': grouped_counts,
        },
    )


def customer_list(request):
    user_email = require_session_user(request)
    if not user_email:
        return redirect(reverse('accounts:login'))

    business = get_or_create_business_for_email(user_email)
    if request.method == 'POST':
        form = CustomerForm(request.POST, business=business)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.business = business
            customer.save()
            messages.success(request, 'Customer added successfully.')
            return redirect(reverse('accounts:customers'))
    else:
        form = CustomerForm(business=business)

    return render(
        request,
        'accounts/customer_list.html',
        {
            'business': business,
            'form': form,
            'customers': business.customers.order_by('name'),
        },
    )


def chat_view(request):
    user_email = require_session_user(request)
    if not user_email:
        return redirect(reverse('accounts:login'))

    business = get_or_create_business_for_email(user_email)

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        if message_text:
            # 1. Save User Message
            user_msg = ChatMessage.objects.create(
                business=business,
                role=ChatMessage.USER,
                message_text=message_text,
                processing_status=ChatMessage.PENDING
            )
            
            # 2. Call AI Parser for Milestone 4
            try:
                res = call_ai_parser(message_text, base_currency=business.base_currency)
                parsed_json, error_msg = res if isinstance(res, tuple) else (res, None)
            except Exception as e:
                parsed_json = None
                error_msg = f"Crash inside views: {e}"
            
            if parsed_json:
                intent = parsed_json.get('intent', 'transaction')
                payload = parsed_json.get('payload', parsed_json)

                if intent == 'report':
                    # Execute Report immediately and return text to user
                    from django.db.models import Sum
                    from datetime import datetime
                    
                    start_date = payload.get('start_date', '2000-01-01')
                    end_date = payload.get('end_date', datetime.today().strftime('%Y-%m-%d'))
                    category = payload.get('category', '').strip()
                    kind = payload.get('kind', 'all')
                    
                    qs = business.transactions.filter(status=Transaction.CONFIRMED, occurred_on__gte=start_date, occurred_on__lte=end_date)
                    if category:
                        qs = qs.filter(category__name__icontains=category)
                    
                    if kind in ['income', 'expense']:
                        qs = qs.filter(kind=kind)
                        
                    total = qs.aggregate(total=Sum('amount'))['total'] or 0
                    
                    response_text = f"Based on your transactions from {start_date} to {end_date}"
                    if category:
                        response_text += f" in the '{category}' category"
                    response_text += f", the total is **{total} {business.base_currency}**."
                    
                    ChatMessage.objects.create(
                        business=business, 
                        role=ChatMessage.ASSISTANT, 
                        message_text=response_text, 
                        processing_status=ChatMessage.CONFIRMED
                    )
                    
                elif intent == 'invoice':
                    # Draft an invoice and return a link
                    from decimal import Decimal
                    from datetime import timedelta, datetime
                    customer_name = payload.get('customer_name', 'New Customer')
                    amount = Decimal(payload.get('amount', '0.00'))
                    desc = payload.get('description', 'Services provided')
                    
                    from .models import Customer, Invoice, InvoiceItem
                    customer_obj, _ = Customer.objects.get_or_create(business=business, name__iexact=customer_name, defaults={'name': customer_name})
                    
                    invoice_obj = Invoice.objects.create(
                        business=business,
                        customer=customer_obj,
                        invoice_number=f"INV-{Invoice.objects.filter(business=business).count()+1001}",
                        status=Invoice.DRAFT,
                        issue_date=datetime.today(),
                        due_date=datetime.today() + timedelta(days=14),
                        currency=business.base_currency,
                        subtotal=amount,
                        tax_amount=Decimal('0.00'),
                        total_amount=amount,
                        notes="Generated by AI Co-Pilot"
                    )
                    
                    InvoiceItem.objects.create(
                        invoice=invoice_obj,
                        description=desc,
                        quantity=Decimal('1.00'),
                        unit_price=amount,
                        total=amount
                    )
                    
                    response_text = f"I've drafted Invoice #{invoice_obj.invoice_number} for {customer_name}. "
                    
                    msg = ChatMessage.objects.create(
                        business=business, 
                        role=ChatMessage.ASSISTANT, 
                        message_text=response_text, 
                        processing_status=ChatMessage.CONFIRMED,
                        parsed_payload={"invoice_id": invoice_obj.id}
                    )
                else:
                    # Default: Transaction
                    ChatMessage.objects.create(
                        business=business, 
                        role=ChatMessage.ASSISTANT, 
                        message_text="I parsed a transaction for you.", 
                        parsed_payload=parsed_json,
                        processing_status=ChatMessage.PENDING
                    )
            else:
                fail_msg = f"Sorry, I could not parse that into a transaction. Error: {error_msg}" if error_msg else f"Sorry, I could not understand that. Input was: {message_text}"
                ChatMessage.objects.create(
                    business=business,
                    role=ChatMessage.ASSISTANT,
                    message_text=fail_msg,
                    processing_status=ChatMessage.FAILED
                )
            
        return redirect(reverse('accounts:chat'))

    messages_list = business.chat_messages.all().order_by('created_at')
    
    return render(
        request,
        'accounts/chat.html',
        {
            'business': business,
            'messages_list': messages_list
        }
    )


def confirm_transaction(request, message_id):
    user_email = require_session_user(request)
    if not user_email:
        return redirect(reverse('accounts:login'))

    business = get_or_create_business_for_email(user_email)
    
    try:
        msg = ChatMessage.objects.get(id=message_id, business=business, role=ChatMessage.ASSISTANT, processing_status=ChatMessage.PENDING)
    except ChatMessage.DoesNotExist:
        messages.error(request, 'Message not found or already verified.')
        return redirect(reverse('accounts:chat'))

    if request.method == 'POST':
        raw_payload = msg.parsed_payload
        if raw_payload:
            payload = raw_payload.get('payload', raw_payload)
            kind = payload.get('kind', Transaction.EXPENSE)
            amount = payload.get('amount')
            currency = payload.get('currency', business.base_currency)
            occurred_on = payload.get('occurred_on')
            counterparty = payload.get('counterparty', '')
            note = payload.get('note', '')
            category_name = payload.get('category_name')
            
            category = None
            if category_name:
                category, _ = Category.objects.get_or_create(
                    business=business, 
                    name=category_name, 
                    kind=kind,
                    defaults={'is_system_default': False}
                )
            
            Transaction.objects.create(
                business=business,
                kind=kind,
                amount=amount,
                currency=currency,
                occurred_on=occurred_on,
                category=category,
                counterparty=counterparty,
                note=note,
                source_message=msg.message_text,
                status=Transaction.CONFIRMED
            )
            
            msg.processing_status = ChatMessage.CONFIRMED
            msg.save()
            messages.success(request, 'Transaction confirmed successfully.')
        
        return redirect(reverse('accounts:chat'))
    
    return redirect(reverse('accounts:chat'))


def invoice_list_view(request):
    user_email = require_session_user(request)
    if not user_email:
        return redirect('accounts:login')
    
    business = get_or_create_business_for_email(user_email)
    invoices = Invoice.objects.filter(business=business).select_related('customer')
    
    return render(request, 'accounts/invoice_list.html', {
        'business': business,
        'invoices': invoices,
    })


def invoice_create_view(request):
    from decimal import Decimal
    user_email = require_session_user(request)
    if not user_email:
        return redirect('accounts:login')
    
    business = get_or_create_business_for_email(user_email)
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, business=business)
        formset = InvoiceItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            invoice = form.save(commit=False)
            invoice.business = business
            
            # temporary saves to allow line item calc
            invoice.subtotal = Decimal('0.00')
            invoice.total_amount = Decimal('0.00')
            invoice.save()
            
            formset.instance = invoice
            items = formset.save(commit=False)
            
            subtotal = Decimal('0.00')
            for item in items:
                item.total = item.quantity * item.unit_price
                subtotal += item.total
                item.save()
                
            for deleted_item in formset.deleted_objects:
                deleted_item.delete()
                
            invoice.subtotal = subtotal
            invoice.total_amount = subtotal + invoice.tax_amount
            invoice.save()
            
            messages.success(request, 'Invoice created successfully.')
            return redirect('accounts:invoice_detail', invoice.id)
    else:
        form = InvoiceForm(business=business)
        formset = InvoiceItemFormSet()
        
    return render(request, 'accounts/invoice_form.html', {
        'business': business,
        'form': form,
        'formset': formset,
    })


def invoice_detail_view(request, invoice_id):
    from django.shortcuts import get_object_or_404
    user_email = require_session_user(request)
    if not user_email:
        return redirect('accounts:login')
    
    business = get_or_create_business_for_email(user_email)
    invoice = get_object_or_404(Invoice, id=invoice_id, business=business)
    items = invoice.items.all()
    
    return render(request, 'accounts/invoice_detail.html', {
        'business': business,
        'invoice': invoice,
        'items': items,
    })


def invoice_mark_paid_view(request, invoice_id):
    from django.shortcuts import get_object_or_404
    user_email = require_session_user(request)
    if not user_email:
        return redirect('accounts:login')
        
    business = get_or_create_business_for_email(user_email)
    invoice = get_object_or_404(Invoice, id=invoice_id, business=business)
    
    if request.method == 'POST':
        invoice.status = Invoice.PAID
        invoice.save()
        
        # Automatically generate a transaction for this payment
        Transaction.objects.create(
            business=business,
            kind=Transaction.INCOME,
            amount=invoice.total_amount,
            currency=invoice.currency,
            occurred_on=invoice.due_date, # Or today
            counterparty=invoice.customer.name,
            note=f"Payment for Invoice #{invoice.invoice_number}",
            status=Transaction.CONFIRMED
        )
        messages.success(request, f'Invoice #{invoice.invoice_number} marked as Paid. Income transaction recorded.')
        
    return redirect('accounts:invoice_detail', invoice_id)


def reports_view(request):
    from django.db.models import Sum
    user_email = require_session_user(request)
    if not user_email:
        return redirect('accounts:login')
        
    business = get_or_create_business_for_email(user_email)
    summary = get_transaction_summary(business)
    
    # Simple expense breakdown by category
    category_breakdown = business.transactions.filter(
        status=Transaction.CONFIRMED,
        kind=Transaction.EXPENSE
    ).values('category__name').annotate(total=Sum('amount')).order_by('-total')
    
    return render(request, 'accounts/reports.html', {
        'business': business,
        'summary': summary,
        'category_breakdown': category_breakdown,
    })
