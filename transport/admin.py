from django.contrib import admin
from .models import Route, Stop, Vehicle, Timetable, Trip, Feedback, Booking

@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'active')
    search_fields = ('name', 'code')
    list_filter = ('active',)
    ordering = ('name',)
    # REMOVED filter_horizontal for vehicles (not a M2M field on Route)

@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'route', 'location')
    search_fields = ('name', 'code', 'location')
    list_filter = ('route',)
    ordering = ('route', 'name')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('code', 'vehicle_type', 'capacity', 'active')
    list_filter = ('vehicle_type', 'active', 'assigned_routes')
    search_fields = ('code',)
    ordering = ('code',)
    filter_horizontal = ('assigned_routes',)  # Correct, as assigned_routes is M2M

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('route', 'stop', 'arrival_time', 'departure_time')
    list_filter = ('route', 'stop')
    ordering = ('route', 'stop', 'arrival_time')
    search_fields = ('route__name', 'stop__name')  # REQUIRED for autocomplete_fields

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'route', 'vehicle', 'scheduled_departure', 'scheduled_arrival',
        'actual_departure', 'actual_arrival', 'available_seats'
    )
    list_filter = ('route', 'vehicle')
    search_fields = ('id',)
    ordering = ('scheduled_departure',)
    autocomplete_fields = ['route', 'vehicle', 'timetable']

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'route', 'trip', 'category', 'submitted_at', 'resolved')
    list_filter = ('category', 'resolved', 'route')
    search_fields = ('description',)
    ordering = ('-submitted_at',)
    autocomplete_fields = ['user', 'route', 'trip']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'trip', 'booked_at', 'status')
    list_filter = ('status', 'trip__route')
    search_fields = ('user__username', 'trip__id')
    ordering = ('-booked_at',)
    autocomplete_fields = ['user', 'trip']