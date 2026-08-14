# bookings/urls.py
from django.urls import path,include
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("hotel/<int:hotel_id>/rooms/", views.room_list, name="room_list"),
    path("hotel/<int:hotel_id>/rate/", views.rate_hotel, name="rate_hotel"),
    path("room/<int:room_id>/book/", views.book_room, name="book_room"),
    # path("payment/", views.payment, name="payment"),
path('payment/<int:booking_id>/', views.payment, name='payment'),
    path("booking/<int:booking_id>/success/", views.booking_success, name="booking_success"),
    path("login/", views.custom_login, name="login"),
    path("logout/", views.custom_logout, name="logout"),
    path("register/", views.register, name="register"),
    path("booking-success/", views.booking_success, name="booking_success"),
    path("my-bookings/", views.my_bookings, name="my_bookings"),
    path("payment/<int:room_id>/", views.payment, name="payment"),
    path("payment-confirm/<int:room_id>/", views.payment_confirm, name="payment_confirm"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("my-bookings/", views.my_bookings, name="my_bookings"),
    path("explore-hotels/", views.home, name="explore_hotels"),
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter_subscribe'),
path("check-availability/", views.check_availability, name="check_availability"),
path('receipt/<int:booking_id>/', views.booking_receipt, name='booking_receipt'),
path('upload-profile/', views.upload_profile_image, name='upload_profile'),
path('payment/<int:booking_id>/', views.fake_payment, name='fake_payment'),
path('payment-success/<int:booking_id>/', views.payment_success, name='payment_success'),
path('invoice/<int:booking_id>/', views.download_invoice, name='download_invoice'),
path('search/', views.search_hotels, name='search_hotels'),
    path("set-currency/", views.set_currency, name="set_currency"),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/calendar/', views.admin_calendar, name='admin_calendar'),
    path('admin-dashboard/calendar/events/', views.admin_calendar_events_api, name='admin_calendar_events_api'),
path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
path(
    'admin-dashboard/hotels/',
    views.admin_hotels,
    name='admin_hotels'
),
path(
    'admin-dashboard/hotels/add/',
    views.admin_add_hotel,
    name='admin_add_hotel'
),
path(
    'admin-dashboard/hotels/edit/<int:hotel_id>/',
    views.admin_edit_hotel,
    name='admin_edit_hotel'
),
path(
    'admin-dashboard/hotels/delete/<int:hotel_id>/',
    views.admin_delete_hotel,
    name='admin_delete_hotel'
),
path(
    'admin-dashboard/rooms/',
    views.admin_rooms,
    name='admin_rooms'
),
path(
    'admin-dashboard/rooms/add/',
    views.admin_add_room,
    name='admin_add_room'
),
path(
    'admin-dashboard/rooms/edit/<int:room_id>/',
    views.admin_edit_room,
    name='admin_edit_room'
),
path(
    'admin-dashboard/rooms/delete/<int:room_id>/',
    views.admin_delete_room,
    name='admin_delete_room'
),

]

