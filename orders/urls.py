from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='list'),
    path('checkout/', views.checkout, name='checkout'),
    path('<str:reference>/confirmation/', views.order_success, name='success'),
    path('<str:reference>/cancel/', views.order_cancel, name='cancel'),
    path('<str:reference>/', views.order_detail, name='detail'),
]
