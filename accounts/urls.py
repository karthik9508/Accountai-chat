from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('transactions/', views.transaction_list, name='transactions'),
    path('transactions/new/', views.transaction_create, name='transaction_create'),
    path('categories/', views.category_list, name='categories'),
    path('customers/', views.customer_list, name='customers'),
    path('chat/', views.chat_view, name='chat'),
    path('chat/confirm/<int:message_id>/', views.confirm_transaction, name='confirm_transaction'),
    path('invoices/', views.invoice_list_view, name='invoice_list'),
    path('invoices/new/', views.invoice_create_view, name='invoice_create'),
    path('invoices/<int:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),
    path('invoices/<int:invoice_id>/pay/', views.invoice_mark_paid_view, name='invoice_mark_paid'),
    path('reports/', views.reports_view, name='reports'),
]
