from django.urls import path
from .views import (
    DashboardView, AnalyticsView,
    FeedbackCreateView, FeedbackListView, FeedbackUpdateView,
    VehicleListView, VehicleDetailView, VehicleCreateView, VehicleUpdateView, VehicleDeleteView,
    TripListView, TripDetailView, TripCreateView, TripUpdateView, TripDeleteView,
    RouteListView, RouteDetailView, RouteCreateView, RouteUpdateView, RouteDeleteView,
    BookingListView, BookingDetailView, BookingCreateView, BookingUpdateView, BookingDeleteView,
)

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),

    # Feedback
    path('feedback/new/', FeedbackCreateView.as_view(), name='feedback-create'),
    path('feedback/', FeedbackListView.as_view(), name='feedback-list'),
    path('feedback/<int:pk>/resolve/', FeedbackUpdateView.as_view(), name='feedback-update'),

    # Vehicles
    path('vehicles/', VehicleListView.as_view(), name='vehicle-list'),
    path('vehicles/<int:pk>/', VehicleDetailView.as_view(), name='vehicle-detail'),
    path('vehicles/add/', VehicleCreateView.as_view(), name='vehicle-add'),
    path('vehicles/<int:pk>/edit/', VehicleUpdateView.as_view(), name='vehicle-edit'),
    path('vehicles/<int:pk>/delete/', VehicleDeleteView.as_view(), name='vehicle-delete'),

    # Trips
    path('trips/', TripListView.as_view(), name='trip-list'),
    path('trips/<int:pk>/', TripDetailView.as_view(), name='trip-detail'),
    path('trips/add/', TripCreateView.as_view(), name='trip-add'),
    path('trips/<int:pk>/edit/', TripUpdateView.as_view(), name='trip-edit'),
    path('trips/<int:pk>/delete/', TripDeleteView.as_view(), name='trip-delete'),

    # Routes
    path('routes/', RouteListView.as_view(), name='route-list'),
    path('routes/<int:pk>/', RouteDetailView.as_view(), name='route-detail'),
    path('routes/add/', RouteCreateView.as_view(), name='route-add'),
    path('routes/<int:pk>/edit/', RouteUpdateView.as_view(), name='route-edit'),
    path('routes/<int:pk>/delete/', RouteDeleteView.as_view(), name='route-delete'),

    # Bookings (client)
    path('bookings/', BookingListView.as_view(), name='booking-list'),
    path('bookings/<int:pk>/', BookingDetailView.as_view(), name='booking-detail'),
    path('bookings/add/', BookingCreateView.as_view(), name='booking-add'),
    path('bookings/<int:pk>/edit/', BookingUpdateView.as_view(), name='booking-edit'),
    path('bookings/<int:pk>/delete/', BookingDeleteView.as_view(), name='booking-delete'),
]