from decimal import Decimal

from django.db.models import Count, Sum

from .models import BusinessProfile, Category, Transaction

DEFAULT_CATEGORY_MAP = {
    Category.EXPENSE: [
        'Fuel',
        'Food',
        'Rent',
        'Utilities',
        'Software',
        'Travel',
        'Marketing',
    ],
    Category.INCOME: [
        'Sales',
        'Consulting',
        'Subscription',
        'Interest',
        'Refund',
    ],
}


def business_name_from_email(email):
    local_part = email.split('@', 1)[0].strip() if email else 'business'
    normalized = local_part.replace('.', ' ').replace('_', ' ').replace('-', ' ')
    words = [word for word in normalized.split() if word]
    return ' '.join(word.capitalize() for word in words) or 'My Business'


def seed_default_categories(business):
    existing_pairs = set(business.categories.values_list('kind', 'name'))
    categories_to_create = []
    for kind, names in DEFAULT_CATEGORY_MAP.items():
        for name in names:
            if (kind, name) not in existing_pairs:
                categories_to_create.append(
                    Category(
                        business=business,
                        name=name,
                        kind=kind,
                        is_system_default=True,
                    )
                )
    if categories_to_create:
        Category.objects.bulk_create(categories_to_create)


def get_or_create_business_for_email(email):
    business, _ = BusinessProfile.objects.get_or_create(
        owner_email=email,
        defaults={'name': business_name_from_email(email)},
    )
    seed_default_categories(business)
    return business


def get_transaction_summary(business):
    confirmed_transactions = business.transactions.filter(status=Transaction.CONFIRMED)
    income_total = confirmed_transactions.filter(kind=Transaction.INCOME).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    expense_total = confirmed_transactions.filter(kind=Transaction.EXPENSE).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    draft_total = business.transactions.filter(status=Transaction.DRAFT).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    return {
        'income_total': income_total,
        'expense_total': expense_total,
        'net_total': income_total - expense_total,
        'draft_total': draft_total,
        'total_transactions': business.transactions.count(),
        'confirmed_count': confirmed_transactions.count(),
        'draft_count': business.transactions.filter(status=Transaction.DRAFT).count(),
        'category_breakdown': list(
            confirmed_transactions.values('category__name', 'kind')
            .annotate(total=Sum('amount'), entries=Count('id'))
            .order_by('-total', 'category__name')[:6]
        ),
        'recent_transactions': list(
            business.transactions.select_related('category').order_by('-occurred_on', '-created_at')[:8]
        ),
    }


def get_transaction_filters(queryset, *, kind='', status=''):
    if kind in {Transaction.INCOME, Transaction.EXPENSE}:
        queryset = queryset.filter(kind=kind)
    if status in {Transaction.DRAFT, Transaction.CONFIRMED}:
        queryset = queryset.filter(status=status)
    return queryset
