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
    # Dashboard (all logged-in)
    path('', DashboardView.as_view(), name='dashboard'),

    # Analytics (staff only)
    path('analytics/', AnalyticsView.as_view(), name='analytics'),

    # Feedback
    path('feedback/new/', FeedbackCreateView.as_view(), name='feedback-create'),  # submit feedback (passenger+staff)
    path('feedback/', FeedbackListView.as_view(), name='feedback-list'),          # manage feedback (staff only)
    path('feedback/<int:pk>/resolve/', FeedbackUpdateView.as_view(), name='feedback-update'),  # resolve feedback (staff only)

    # Vehicles (view: all, manage: staff)
    path('vehicles/', VehicleListView.as_view(), name='vehicle-list'),            # all users
    path('vehicles/<int:pk>/', VehicleDetailView.as_view(), name='vehicle-detail'), # all users
    path('vehicles/add/', VehicleCreateView.as_view(), name='vehicle-add'),       # staff only
    path('vehicles/<int:pk>/edit/', VehicleUpdateView.as_view(), name='vehicle-edit'), # staff only
    path('vehicles/<int:pk>/delete/', VehicleDeleteView.as_view(), name='vehicle-delete'), # staff only

    # Trips (view: all, manage: staff)
    path('trips/', TripListView.as_view(), name='trip-list'),                     # all users
    path('trips/<int:pk>/', TripDetailView.as_view(), name='trip-detail'),        # all users
    path('trips/add/', TripCreateView.as_view(), name='trip-add'),                # staff only
    path('trips/<int:pk>/edit/', TripUpdateView.as_view(), name='trip-edit'),     # staff only
    path('trips/<int:pk>/delete/', TripDeleteView.as_view(), name='trip-delete'), # staff only

    # Routes (view: all, manage: staff)
    path('routes/', RouteListView.as_view(), name='route-list'),                  # all users
    path('routes/<int:pk>/', RouteDetailView.as_view(), name='route-detail'),     # all users
    path('routes/add/', RouteCreateView.as_view(), name='route-add'),             # staff only
    path('routes/<int:pk>/edit/', RouteUpdateView.as_view(), name='route-edit'),  # staff only
    path('routes/<int:pk>/delete/', RouteDeleteView.as_view(), name='route-delete'), # staff only

    # Bookings (passenger only)
    path('bookings/', BookingListView.as_view(), name='booking-list'),            # passenger dashboard
    path('bookings/<int:pk>/', BookingDetailView.as_view(), name='booking-detail'),# passenger only
    path('bookings/add/', BookingCreateView.as_view(), name='booking-add'),       # passenger only
    path('bookings/<int:pk>/edit/', BookingUpdateView.as_view(), name='booking-edit'), # passenger only
    path('bookings/<int:pk>/delete/', BookingDeleteView.as_view(), name='booking-delete'), # passenger only
]