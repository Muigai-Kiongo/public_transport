from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from .models import Trip, Feedback, Route, Vehicle, Booking
from .forms import FeedbackForm
from django.db import models

# --- Permission Mixins ---
class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

# --- Home/Dashboard ---
class DashboardView(ListView):
    model = Trip
    template_name = 'dashboard/dashboard.html'
    context_object_name = 'trips'
    paginate_by = 20

    def get_queryset(self):
        # Show upcoming and ongoing trips, ordered by scheduled_departure
        return Trip.objects.order_by('-scheduled_departure')[:20]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['routes'] = Route.objects.filter(active=True)
        context['vehicles'] = Vehicle.objects.filter(active=True)
        context['feedbacks'] = Feedback.objects.order_by('-submitted_at')[:10]
        return context

# --- Analytics (staff only) ---
class AnalyticsView(StaffRequiredMixin, LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Avg, Count, ExpressionWrapper, DurationField, F
        delays = Trip.objects.filter(
            actual_arrival__isnull=False,
            scheduled_arrival__isnull=False
        ).annotate(
            delay=ExpressionWrapper(
                F('actual_arrival') - F('scheduled_arrival'),
                output_field=DurationField()
            )
        )
        context['avg_delays'] = (
            delays.values('route__name')
            .annotate(avg_delay=Avg('delay'))
        )
        context['feedback_stats'] = (
            Feedback.objects.values('category').annotate(count=Count('id'))
        )
        context['vehicle_counts'] = (
            Vehicle.objects.values('vehicle_type').annotate(count=Count('id'))
        )
        return context

# --- Feedback ---
class FeedbackCreateView(LoginRequiredMixin, CreateView):
    model = Feedback
    form_class = FeedbackForm
    template_name = 'feedback/feedback_form.html'
    success_url = reverse_lazy('dashboard:dashboard')

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user
        return super().form_valid(form)

class FeedbackListView(StaffRequiredMixin, ListView):
    model = Feedback
    template_name = 'feedback/feedback_list.html'
    context_object_name = 'feedbacks'
    paginate_by = 20

class FeedbackUpdateView(StaffRequiredMixin, UpdateView):
    model = Feedback
    fields = ['resolved']
    template_name = 'feedback/feedback_update.html'
    success_url = reverse_lazy('dashboard:feedback-list')

# --- Vehicle CRUD (staff only for create/update/delete) ---
class VehicleListView(LoginRequiredMixin, ListView):
    model = Vehicle
    template_name = 'dashboard/vehicle_list.html'
    context_object_name = 'vehicles'

class VehicleDetailView(LoginRequiredMixin, DetailView):
    model = Vehicle
    template_name = 'dashboard/vehicle_detail.html'
    context_object_name = 'vehicle'

class VehicleCreateView(StaffRequiredMixin, CreateView):
    model = Vehicle
    fields = ['code', 'vehicle_type', 'capacity', 'active', 'assigned_routes']
    template_name = 'dashboard/vehicle_form.html'
    success_url = reverse_lazy('dashboard:vehicle-list')

class VehicleUpdateView(StaffRequiredMixin, UpdateView):
    model = Vehicle
    fields = ['code', 'vehicle_type', 'capacity', 'active', 'assigned_routes']
    template_name = 'dashboard/vehicle_form.html'
    success_url = reverse_lazy('dashboard:vehicle-list')

class VehicleDeleteView(StaffRequiredMixin, DeleteView):
    model = Vehicle
    template_name = 'dashboard/vehicle_confirm_delete.html'
    success_url = reverse_lazy('dashboard:vehicle-list')

# --- Trip CRUD (staff only for create/update/delete) ---
class TripListView(LoginRequiredMixin, ListView):
    model = Trip
    template_name = 'dashboard/trip_list.html'
    context_object_name = 'trips'

class TripDetailView(LoginRequiredMixin, DetailView):
    model = Trip
    template_name = 'dashboard/trip_detail.html'
    context_object_name = 'trip'

class TripCreateView(StaffRequiredMixin, CreateView):
    model = Trip
    fields = ['route', 'vehicle', 'scheduled_departure', 'scheduled_arrival', 'timetable', 'available_seats']
    template_name = 'dashboard/trip_form.html'
    success_url = reverse_lazy('dashboard:trip-list')

class TripUpdateView(StaffRequiredMixin, UpdateView):
    model = Trip
    fields = ['route', 'vehicle', 'scheduled_departure', 'scheduled_arrival', 'timetable', 'available_seats']
    template_name = 'dashboard/trip_form.html'
    success_url = reverse_lazy('dashboard:trip-list')

class TripDeleteView(StaffRequiredMixin, DeleteView):
    model = Trip
    template_name = 'dashboard/trip_confirm_delete.html'
    success_url = reverse_lazy('dashboard:trip-list')

# --- Route CRUD (staff only for create/update/delete) ---
class RouteListView(LoginRequiredMixin, ListView):
    model = Route
    template_name = 'dashboard/route_list.html'
    context_object_name = 'routes'

class RouteDetailView(LoginRequiredMixin, DetailView):
    model = Route
    template_name = 'dashboard/route_detail.html'
    context_object_name = 'route'

class RouteCreateView(StaffRequiredMixin, CreateView):
    model = Route
    fields = ['name', 'code', 'description', 'active']
    template_name = 'dashboard/route_form.html'
    success_url = reverse_lazy('dashboard:route-list')

class RouteUpdateView(StaffRequiredMixin, UpdateView):
    model = Route
    fields = ['name', 'code', 'description', 'active']
    template_name = 'dashboard/route_form.html'
    success_url = reverse_lazy('dashboard:route-list')

class RouteDeleteView(StaffRequiredMixin, DeleteView):
    model = Route
    template_name = 'dashboard/route_confirm_delete.html'
    success_url = reverse_lazy('dashboard:route-list')

# --- Booking CRUD (all authenticated users) ---
class BookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = 'dashboard/booking_list.html'
    context_object_name = 'bookings'

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

class BookingDetailView(LoginRequiredMixin, DetailView):
    model = Booking
    template_name = 'dashboard/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

class BookingCreateView(LoginRequiredMixin, CreateView):
    model = Booking
    fields = ['trip']
    template_name = 'dashboard/booking_form.html'
    success_url = reverse_lazy('dashboard:booking-list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class BookingUpdateView(LoginRequiredMixin, UpdateView):
    model = Booking
    fields = ['status']
    template_name = 'dashboard/booking_form.html'
    success_url = reverse_lazy('dashboard:booking-list')

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

class BookingDeleteView(LoginRequiredMixin, DeleteView):
    model = Booking
    template_name = 'dashboard/booking_confirm_delete.html'
    success_url = reverse_lazy('dashboard:booking-list')

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)