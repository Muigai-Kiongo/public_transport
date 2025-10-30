import json
import threading
import logging

from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction, IntegrityError
from django.db.models import F
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden

from .models import Trip, Feedback, Route, Vehicle, Booking
from .forms import FeedbackForm

logger = logging.getLogger(__name__)


# --- Permission Mixins ---
class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


class PassengerRequiredMixin(UserPassesTestMixin, LoginRequiredMixin):
    def test_func(self):
        return self.request.user.is_authenticated and not self.request.user.is_staff


# --- Home/Dashboard ---
class DashboardView(LoginRequiredMixin, ListView):
    model = Trip
    template_name = 'dashboard/dashboard.html'
    context_object_name = 'trips'
    paginate_by = 20

    def get_queryset(self):
        return Trip.objects.order_by('-scheduled_departure')[:20]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['routes'] = Route.objects.filter(active=True)
        context['vehicles'] = Vehicle.objects.filter(active=True)
        context['feedbacks'] = Feedback.objects.order_by('-submitted_at')[:10]
        return context


# --- Analytics (staff only) ---
class AnalyticsView(StaffRequiredMixin, TemplateView):
    template_name = 'dashboard/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Avg, Count, ExpressionWrapper, DurationField, F as _F
        delays = Trip.objects.filter(
            actual_arrival__isnull=False,
            scheduled_arrival__isnull=False
        ).annotate(
            delay=ExpressionWrapper(
                _F('actual_arrival') - _F('scheduled_arrival'),
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


# --- Vehicle Views ---
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


# --- Trip Views ---
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


# --- Route Views ---
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


# --- Email helpers for booking confirmations ---
def _send_email_async(subject, text_body, html_body, from_email, to_list):
    """
    Internal: send email in a background thread to avoid blocking the request.
    """
    try:
        msg = EmailMultiAlternatives(subject, text_body, from_email, to_list)
        if html_body:
            msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        logger.info("Booking confirmation email sent to %s", to_list)
    except Exception as exc:
        logger.exception("Error sending booking confirmation email to %s: %s", to_list, exc)


def send_booking_confirmation_email(booking):
    """
    Compose and dispatch a booking confirmation email to booking.user.email.
    Requires templates/emails/booking_confirmation.txt and .html to exist.
    """
    if booking is None:
        logger.warning("send_booking_confirmation_email called with None")
        return

    user = getattr(booking, "user", None)
    if not user or not getattr(user, "email", None):
        logger.info("No user email available for booking %s; skipping email", getattr(booking, "pk", None))
        return

    recipient = user.email
    subject = f"Booking Confirmed — #{booking.pk} ({booking.trip.route.name})"
    context = {
        "booking": booking,
        "user": user,
        "trip": booking.trip,
        "site_name": getattr(settings, "DEFAULT_FROM_EMAIL", "Transport Dashboard"),
    }

    # Render templates (plain text + HTML). If templates missing, fallback to minimal text.
    try:
        text_body = render_to_string("emails/booking_confirmation.txt", context)
    except Exception:
        vehicle_code = booking.trip.vehicle.code if booking.trip and booking.trip.vehicle else "—"
        text_body = (
            f"Booking confirmation — #{booking.pk}\n\n"
            f"Route: {booking.trip.route.name}\n"
            f"Vehicle: {vehicle_code}\n"
            f"Departure: {booking.trip.scheduled_departure}\n"
            f"Arrival: {booking.trip.scheduled_arrival}\n"
            f"Status: {booking.get_status_display()}\n"
            f"Seat: {booking.seat_number or 'TBD'}\n"
        )

    try:
        html_body = render_to_string("emails/booking_confirmation.html", context)
    except Exception:
        html_body = None

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER)
    # send in background thread
    thread = threading.Thread(
        target=_send_email_async,
        args=(subject, text_body, html_body, from_email, [recipient]),
        daemon=True,
    )
    thread.start()


# --- Booking Views (passenger only) ---
class BookingListView(PassengerRequiredMixin, ListView):
    model = Booking
    template_name = 'dashboard/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 10  # sensible default

    def get_queryset(self):
        # prefetch/select related to reduce DB queries in the template
        return (
            Booking.objects.filter(user=self.request.user)
            .select_related('trip__route', 'trip__vehicle')
            .order_by('-booked_at')
        )


class BookingDetailView(PassengerRequiredMixin, DetailView):
    """
    BookingDetail provides `booked_seats_json` and `vehicle_capacity` in context
    so the template can embed a safe JSON list (avoids calling queryset methods
    inside the template which causes the TemplateSyntaxError).
    """
    model = Booking
    template_name = 'dashboard/booking_detail.html'
    context_object_name = 'booking'

    def get_queryset(self):
        # select related to reduce queries
        return Booking.objects.filter(user=self.request.user).select_related('trip__route', 'trip__vehicle')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        booking = context.get('booking') or self.get_object()
        trip = getattr(booking, 'trip', None)

        # Default values
        context['booked_seats_json'] = json.dumps([])
        context['vehicle_capacity'] = 0

        if trip:
            booked_qs = Booking.objects.filter(trip=trip, seat_number__isnull=False).values_list('seat_number', flat=True)
            try:
                booked_seats = [int(s) for s in booked_qs if s is not None]
            except Exception:
                booked_seats = []
            context['booked_seats_json'] = json.dumps(booked_seats)
            context['vehicle_capacity'] = trip.vehicle.capacity if getattr(trip, 'vehicle', None) else 0

        return context


def trip_seat_map_json(request):
    """
    JSON endpoint returning a simple seat map for a trip.

    Query params:
      - trip: trip id (required)

    Response:
      {
        "trip": <id>,
        "capacity": <int>,
        "booked_seats": [1,2,3],
        "available": <int>
      }
    """
    # only allow authenticated users to access seat map
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'authentication required'}, status=401)

    trip_id = request.GET.get('trip')
    if not trip_id:
        return HttpResponseBadRequest("Missing 'trip' parameter")

    try:
        trip = Trip.objects.select_related('vehicle').get(pk=int(trip_id))
    except (Trip.DoesNotExist, ValueError):
        return HttpResponseBadRequest("Invalid trip id")

    vehicle = trip.vehicle
    capacity = vehicle.capacity if vehicle else 0

    # collect booked seat numbers for this trip
    booked_qs = Booking.objects.filter(trip=trip, seat_number__isnull=False).values_list('seat_number', flat=True)
    booked = sorted([int(s) for s in booked_qs if s is not None])

    # compute available seats (simple)
    available = max(0, trip.available_seats)

    payload = {
        'trip': trip.pk,
        'capacity': capacity,
        'booked_seats': booked,
        'available': available,
    }
    return JsonResponse(payload)


class BookingCreateView(PassengerRequiredMixin, CreateView):
    """
    Booking creation with transactional seat allocation. Accepts optional
    seat_number from the form (client-side seat-picker); otherwise auto-assigns.
    """
    model = Booking
    form_class = None  # will be set in dispatch to BookingForm
    template_name = 'dashboard/booking_form.html'
    success_url = reverse_lazy('dashboard:booking-list')

    # retry a few times on IntegrityError (unique constraint race)
    ALLOCATE_RETRIES = 3

    def dispatch(self, request, *args, **kwargs):
        # import BookingForm here to avoid circular imports if any
        from .forms import BookingForm
        self.form_class = BookingForm
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # pass current user into the form in case it needs it
        kwargs.setdefault('user', self.request.user)
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        trip = form.cleaned_data.get('trip')
        requested_seat = form.cleaned_data.get('seat_number') or None

        if trip is None:
            form.add_error('trip', 'Please select a trip.')
            return self.form_invalid(form)

        attempt = 0
        while attempt < self.ALLOCATE_RETRIES:
            attempt += 1
            try:
                with transaction.atomic():
                    trip_locked = Trip.objects.select_for_update().get(pk=trip.pk)

                    if trip_locked.available_seats <= 0:
                        form.add_error(None, 'Sorry, no seats are available on this trip.')
                        return self.form_invalid(form)

                    vehicle = trip_locked.vehicle
                    vehicle_capacity = vehicle.capacity if vehicle else 0

                    # existing booked seats
                    booked_seats = set(Booking.objects.filter(trip=trip_locked, seat_number__isnull=False).values_list('seat_number', flat=True))

                    # If user picked a seat, try to reserve it
                    assigned_seat = None
                    if requested_seat:
                        try:
                            requested_seat = int(requested_seat)
                        except (TypeError, ValueError):
                            form.add_error('seat_number', 'Invalid seat selection.')
                            return self.form_invalid(form)

                        # Optional: enforce upper bound if vehicle capacity is known
                        if vehicle_capacity and requested_seat > vehicle_capacity and requested_seat > (max(booked_seats) + 100 if booked_seats else 100):
                            # very large seat numbers are suspicious; reject
                            form.add_error('seat_number', 'Selected seat number is out of expected range.')
                            return self.form_invalid(form)

                        if requested_seat in booked_seats:
                            form.add_error('seat_number', 'Selected seat is already taken. Please choose another.')
                            return self.form_invalid(form)

                        if requested_seat <= 0:
                            form.add_error('seat_number', 'Selected seat is invalid.')
                            return self.form_invalid(form)

                        assigned_seat = requested_seat
                    else:
                        # allocate first free seat
                        for s in range(1, (vehicle_capacity or 1) + 1):
                            if s not in booked_seats:
                                assigned_seat = s
                                break
                        if assigned_seat is None:
                            assigned_seat = (max(booked_seats) + 1) if booked_seats else 1

                    # decrement available seats (use F() to avoid races)
                    trip_locked.available_seats = F('available_seats') - 1
                    trip_locked.save(update_fields=['available_seats'])

                    # create booking
                    booking = form.save(commit=False)
                    booking.user = self.request.user
                    booking.seat_number = assigned_seat
                    booking.status = 'confirmed'
                    booking.save()

                    self.object = booking

                    # send confirmation email asynchronously (non-blocking)
                    try:
                        send_booking_confirmation_email(booking)
                    except Exception:
                        logger.exception("Failed to dispatch booking confirmation email for booking %s", booking.pk)

                    return super().form_valid(form)

            except IntegrityError as ie:
                # unique constraint conflict: retry
                logger.warning("IntegrityError allocating seat for trip %s attempt %s: %s", trip.pk, attempt, ie)
                if attempt >= self.ALLOCATE_RETRIES:
                    form.add_error(None, 'Could not allocate a seat due to high concurrency. Please try again.')
                    return self.form_invalid(form)
                # otherwise retry

            except Trip.DoesNotExist:
                form.add_error('trip', 'Selected trip does not exist.')
                return self.form_invalid(form)

            except Exception as exc:
                logger.exception("Unexpected error while creating booking for trip %s: %s", getattr(trip, 'pk', None), exc)
                form.add_error(None, 'An unexpected error occurred. Please try again.')
                return self.form_invalid(form)

        form.add_error(None, 'Failed to allocate seat; please try again.')
        return self.form_invalid(form)


class BookingUpdateView(PassengerRequiredMixin, UpdateView):
    model = Booking
    fields = ['status']
    template_name = 'dashboard/booking_form.html'
    success_url = reverse_lazy('dashboard:booking-list')

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

    def form_valid(self, form):
        """
        If the user cancels a booking (status -> 'cancelled'), release seat and increment available_seats.
        """
        old = self.get_object()
        old_status = old.status
        response = super().form_valid(form)
        new_status = form.instance.status

        if old_status != 'cancelled' and new_status == 'cancelled':
            try:
                # release seat and increment seats
                old.release_seat_and_increment()
            except Exception:
                logger.exception("Failed to release seat for booking %s on cancellation", old.pk)
        return response


class BookingDeleteView(PassengerRequiredMixin, DeleteView):
    model = Booking
    template_name = 'dashboard/booking_confirm_delete.html'
    success_url = reverse_lazy('dashboard:booking-list')

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        # release seat and increment availability before deletion
        try:
            obj.release_seat_and_increment()
        except Exception:
            logger.exception("Failed to release seat for booking %s on delete", obj.pk)
        return super().delete(request, *args, **kwargs)