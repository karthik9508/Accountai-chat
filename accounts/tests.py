from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from .forms import TransactionForm
from .models import Category, Transaction
from .services import get_or_create_business_for_email, get_transaction_summary


class BusinessServicesTests(TestCase):
    def test_get_or_create_business_seeds_default_categories(self):
        business = get_or_create_business_for_email('owner@example.com')

        self.assertEqual(business.name, 'Owner')
        self.assertGreaterEqual(business.categories.count(), 5)
        self.assertTrue(business.categories.filter(kind=Category.EXPENSE).exists())
        self.assertTrue(business.categories.filter(kind=Category.INCOME).exists())

    def test_summary_uses_confirmed_transactions_for_totals(self):
        business = get_or_create_business_for_email('owner@example.com')
        income_category = business.categories.filter(kind=Category.INCOME).first()
        expense_category = business.categories.filter(kind=Category.EXPENSE).first()

        Transaction.objects.create(
            business=business,
            kind=Transaction.INCOME,
            amount=Decimal('5000.00'),
            currency='INR',
            occurred_on='2026-04-12',
            category=income_category,
            status=Transaction.CONFIRMED,
        )
        Transaction.objects.create(
            business=business,
            kind=Transaction.EXPENSE,
            amount=Decimal('1200.00'),
            currency='INR',
            occurred_on='2026-04-12',
            category=expense_category,
            status=Transaction.CONFIRMED,
        )
        Transaction.objects.create(
            business=business,
            kind=Transaction.EXPENSE,
            amount=Decimal('300.00'),
            currency='INR',
            occurred_on='2026-04-12',
            category=expense_category,
            status=Transaction.DRAFT,
        )

        summary = get_transaction_summary(business)

        self.assertEqual(summary['income_total'], Decimal('5000.00'))
        self.assertEqual(summary['expense_total'], Decimal('1200.00'))
        self.assertEqual(summary['net_total'], Decimal('3800.00'))
        self.assertEqual(summary['draft_total'], Decimal('300.00'))


class TransactionFormTests(TestCase):
    def test_transaction_form_rejects_mismatched_category_kind(self):
        business = get_or_create_business_for_email('owner@example.com')
        income_category = business.categories.filter(kind=Category.INCOME).first()
        form = TransactionForm(
            data={
                'kind': Transaction.EXPENSE,
                'amount': '99.00',
                'currency': 'INR',
                'occurred_on': '2026-04-12',
                'category': income_category.id,
                'counterparty': 'Vendor',
                'note': '',
                'status': Transaction.CONFIRMED,
            },
            business=business,
        )

        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)


class TransactionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        session = self.client.session
        session['supabase_user'] = 'owner@example.com'
        session.save()

    def test_transaction_create_view_saves_a_transaction(self):
        business = get_or_create_business_for_email('owner@example.com')
        expense_category = business.categories.filter(kind=Category.EXPENSE).first()

        response = self.client.post(
            reverse('accounts:transaction_create'),
            data={
                'kind': Transaction.EXPENSE,
                'amount': '450.00',
                'currency': 'INR',
                'occurred_on': '2026-04-12',
                'category': expense_category.id,
                'counterparty': 'Fuel Station',
                'note': 'Office travel',
                'status': Transaction.CONFIRMED,
            },
        )

        self.assertRedirects(response, reverse('accounts:transactions'))
        self.assertEqual(Transaction.objects.count(), 1)
        transaction = Transaction.objects.get()
        self.assertEqual(transaction.business, business)
        self.assertEqual(transaction.counterparty, 'Fuel Station')

    def test_transaction_list_requires_session_login(self):
        anonymous_client = Client()
        response = anonymous_client.get(reverse('accounts:transactions'))

        self.assertRedirects(response, reverse('accounts:login'))
