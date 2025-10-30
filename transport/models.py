from django.db import models, transaction
from django.contrib.auth.models import User
from django.db.models import F

class Route(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Stop(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    location = models.CharField(max_length=255, blank=True)
    route = models.ForeignKey(Route, related_name='stops', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = (
        ('bus', 'Bus'),
        ('train', 'Train'),
    )
    code = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPE_CHOICES)
    capacity = models.PositiveIntegerField()
    active = models.BooleanField(default=True)
    assigned_routes = models.ManyToManyField(Route, related_name='vehicles', blank=True)

    def __str__(self):
        return f"{self.vehicle_type.title()} {self.code}"

class Timetable(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    stop = models.ForeignKey(Stop, on_delete=models.CASCADE)
    arrival_time = models.TimeField()
    departure_time = models.TimeField()

    def __str__(self):
        return f"{self.route} - {self.stop} {self.arrival_time}-{self.departure_time}"

class Trip(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True)
    scheduled_departure = models.DateTimeField()
    scheduled_arrival = models.DateTimeField()
    actual_departure = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)
    timetable = models.ForeignKey(Timetable, on_delete=models.SET_NULL, null=True, blank=True)
    available_seats = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Trip {self.id} on {self.route.name}"

    def save(self, *args, **kwargs):
        """
        Ensure available_seats defaults to the vehicle capacity in sensible cases:

        - On create (no pk yet) if available_seats is falsy (None or 0) and vehicle has capacity,
          set available_seats = vehicle.capacity.

        - On update, if the vehicle was changed and the previous available_seats equals the old
          vehicle.capacity (i.e. it was the default), update available_seats to the new vehicle.capacity.

        This preserves manually adjusted available_seats while keeping sensible defaults when
        trips are created or when the vehicle is switched and the previous value was merely
        the old vehicle's capacity.
        """
        new_vehicle = getattr(self, 'vehicle', None)
        new_capacity = getattr(new_vehicle, 'capacity', None) if new_vehicle else None

        # If creating a new Trip and available_seats is not provided (or 0),
        # default to vehicle.capacity when available.
        if self.pk is None:
            if (self.available_seats in (None, 0)) and new_capacity:
                self.available_seats = int(new_capacity)
        else:
            # Existing Trip: if vehicle changed and prior available_seats matched old capacity,
            # update to new capacity so defaults follow the vehicle change.
            try:
                old = Trip.objects.select_related('vehicle').get(pk=self.pk)
            except Trip.DoesNotExist:
                old = None

            if old:
                old_vehicle = getattr(old, 'vehicle', None)
                old_capacity = getattr(old_vehicle, 'capacity', None) if old_vehicle else None

                if old.vehicle_id != getattr(self, 'vehicle_id', None):
                    # Only override if the previous available_seats looked like the old default
                    if old_capacity is not None and old.available_seats == old_capacity:
                        if new_capacity:
                            self.available_seats = int(new_capacity)
                        else:
                            # New vehicle has no capacity set — set to 0 (or keep previous if you prefer)
                            self.available_seats = 0

        super().save(*args, **kwargs)

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True, blank=True)
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.CharField(max_length=50, choices=[
        ("delay", "Delay"),
        ("comfort", "Comfort"),
        ("cleanliness", "Cleanliness"),
        ("other", "Other"),
    ], default="other")
    description = models.TextField()
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback #{self.id} by {self.user or 'Anon'}"

class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='bookings')
    booked_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Seat mapping: assigned seat number (nullable until assigned)
    seat_number = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            # Prevent the same seat number being assigned twice for the same trip
            models.UniqueConstraint(fields=['trip', 'seat_number'], name='unique_trip_seat')
        ]

    def __str__(self):
        seat = f" seat #{self.seat_number}" if self.seat_number else ""
        return f"Booking #{self.id} by {self.user.username} for Trip {self.trip.id}{seat}"

    def assign_seat_and_confirm(self, seat_number):
        """
        Assign the given seat_number and mark booking confirmed.
        Use inside a transaction with trip locked (select_for_update) to avoid races,
        or rely on DB unique constraint + retries.
        """
        with transaction.atomic():
            # Lock trip row
            trip_locked = Trip.objects.select_for_update().get(pk=self.trip.pk)
            # decrement available seats defensively
            trip_locked.available_seats = F('available_seats') - 1
            trip_locked.save(update_fields=['available_seats'])
            # assign seat and confirm booking
            self.seat_number = seat_number
            self.status = 'confirmed'
            self.save(update_fields=['seat_number', 'status'])

    def release_seat_and_increment(self):
        """
        Release seat (set to null) and increment trip.available_seats.
        Use inside transaction or will lock trip row here.
        """
        if self.seat_number is None:
            return
        with transaction.atomic():
            trip_locked = Trip.objects.select_for_update().get(pk=self.trip.pk)
            trip_locked.available_seats = F('available_seats') + 1
            trip_locked.save(update_fields=['available_seats'])
            self.seat_number = None
            self.save(update_fields=['seat_number'])