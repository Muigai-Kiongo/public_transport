from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

from .models import Feedback, Route, Trip, Booking


class FeedbackForm(forms.ModelForm):
    """
    Feedback form with optional dynamic trip queryset filtering based on a provided
    `route` argument. Widgets include Tailwind-friendly classes so templates can
    render {{ form }} without manually adding classes.
    """
    class Meta:
        model = Feedback
        fields = ['route', 'trip', 'category', 'description']
        widgets = {
            'route': forms.Select(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-transport-blue'
            }),
            'trip': forms.Select(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-transport-blue'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-transport-blue'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-transport-blue',
                'rows': 4
            }),
        }
        labels = {
            'route': 'Route (optional)',
            'trip': 'Trip (optional)',
            'category': 'Category',
            'description': 'Describe the issue or feedback',
        }
        help_texts = {
            'route': 'Choose a route if feedback is related to a specific route.',
            'trip': 'Optionally pick a trip if the feedback refers to a particular trip.',
        }

    def __init__(self, *args, **kwargs):
        """
        Accept an optional `route` kwarg to filter trip choices to that route
        and optional `user` to tailor defaults if needed.
        """
        route = kwargs.pop('route', None)
        super().__init__(*args, **kwargs)

        # sensible default querysets
        self.fields['route'].queryset = Route.objects.order_by('name')
        default_trip_qs = Trip.objects.order_by('scheduled_departure')
        self.fields['trip'].queryset = default_trip_qs

        # If a route instance (or primary key) was passed, filter trips
        if route is not None:
            if isinstance(route, Route):
                self.fields['trip'].queryset = default_trip_qs.filter(route=route)
            else:
                try:
                    self.fields['trip'].queryset = default_trip_qs.filter(route__pk=int(route))
                except Exception:
                    self.fields['trip'].queryset = default_trip_qs

        # route/trip optional in the form
        self.fields['route'].required = False
        self.fields['trip'].required = False

    def clean(self):
        cleaned = super().clean()
        route = cleaned.get('route')
        trip = cleaned.get('trip')

        if trip and route and getattr(trip, 'route_id', None) != getattr(route, 'id', None):
            self.add_error('trip', _('Selected trip does not belong to the selected route.'))

        return cleaned


class BookingForm(forms.ModelForm):
    """
    Booking form used by the seat-map UI. Exposes:
      - trip (ModelChoice)
      - seat_number (optional Integer, HiddenInput)

    Server validates:
      - trip has available seats
      - requested seat (if provided) is within capacity and not already booked
    """
    seat_number = forms.IntegerField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Booking
        fields = ['trip', 'seat_number']
        widgets = {
            'trip': forms.Select(attrs={
                'class': 'w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-transport-blue'
            }),
        }
        labels = {
            'trip': 'Trip',
            'seat_number': 'Seat number (hidden)',
        }
        help_texts = {
            'seat_number': 'Optional — if you select a seat on the map it will be submitted here.',
        }

    def __init__(self, *args, **kwargs):
        """
        Accept optional kwargs:
          - user: the requesting user (not required, but may be used for business rules)
        """
        self.request_user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Default trip queryset: upcoming trips ordered by departure
        self.fields['trip'].queryset = Trip.objects.order_by('scheduled_departure')

    def clean_trip(self):
        trip = self.cleaned_data.get('trip')
        if trip is None:
            raise ValidationError(_('Please select a trip.'))
        if trip.available_seats <= 0:
            raise ValidationError(_('Sorry, no seats are available on this trip.'))
        return trip

    def clean_seat_number(self):
        seat = self.cleaned_data.get('seat_number')
        # allow blank (auto-assign)
        if seat in (None, ''):
            return None
        try:
            seat = int(seat)
        except (TypeError, ValueError):
            raise ValidationError(_('Selected seat is invalid.'))
        if seat <= 0:
            raise ValidationError(_('Selected seat must be a positive number.'))
        return seat

    def clean(self):
        cleaned = super().clean()
        trip = cleaned.get('trip')
        seat = cleaned.get('seat_number')

        if trip is None:
            return cleaned  # trip validation will have added an error

        vehicle = getattr(trip, 'vehicle', None)
        vehicle_capacity = vehicle.capacity if vehicle else 0

        # If a seat was requested, validate it against current bookings and capacity
        if seat:
            # If vehicle has capacity > 0, enforce an upper bound
            if vehicle_capacity and seat > vehicle_capacity:
                self.add_error('seat_number', _('Selected seat exceeds vehicle capacity.'))
                return cleaned

            # Check if seat already taken on this trip
            exists = Booking.objects.filter(trip=trip, seat_number=seat).exists()
            if exists:
                self.add_error('seat_number', _('Selected seat is already taken. Please choose another.'))

        return cleaned


class ProfileForm(forms.ModelForm):
    """
    Simple user profile form for editing username, first/last name and email.
    Validates email uniqueness (excluding the current user).
    """
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'username'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
        }
        help_texts = {
            'username': _('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
            'email': _('We will send booking confirmations to this address.'),
        }

    def __init__(self, *args, **kwargs):
        # accept current_user to exclude from uniqueness checks
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError(_('Please provide an email address.'))
        qs = User.objects.filter(email__iexact=email)
        if self.current_user:
            qs = qs.exclude(pk=self.current_user.pk)
        if qs.exists():
            raise ValidationError(_('This email address is already in use.'))
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError(_('Please provide a username.'))
        qs = User.objects.filter(username__iexact=username)
        if self.current_user:
            qs = qs.exclude(pk=self.current_user.pk)
        if qs.exists():
            raise ValidationError(_('This username is already taken.'))
        return username