from django.db import models
from django.contrib.auth.models import User

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

    def __str__(self):
        return f"Booking #{self.id} by {self.user.username} for Trip {self.trip.id}"