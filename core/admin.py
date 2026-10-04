from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Location, HistoricalFloodRecord, FloodReport, FloodPrediction, Alert, EmergencyResponse


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number')}),
    )
    list_display = ('username', 'email', 'role', 'is_staff')


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'ward', 'latitude', 'longitude', 'created_at')
    search_fields = ('name', 'ward')


@admin.register(HistoricalFloodRecord)
class HistoricalFloodRecordAdmin(admin.ModelAdmin):
    list_display = ('location', 'flood_date', 'water_level_recorded', 'rainfall_mm_recorded')
    list_filter = ('location',)
    search_fields = ('location__name', 'description')
    ordering = ('-flood_date',)


@admin.register(FloodReport)
class FloodReportAdmin(admin.ModelAdmin):
    list_display = ('location', 'reported_by', 'severity', 'status', 'reported_at')
    list_filter = ('severity', 'status')
    search_fields = ('location__name', 'description')


@admin.register(FloodPrediction)
class FloodPredictionAdmin(admin.ModelAdmin):
    list_display = ('location', 'risk_level', 'rainfall_mm', 'water_level', 'matched_historical_flood', 'predicted_at')
    list_filter = ('risk_level',)


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('location', 'sent_at', 'is_active')
    list_filter = ('is_active',)


@admin.register(EmergencyResponse)
class EmergencyResponseAdmin(admin.ModelAdmin):
    list_display = ('flood_report', 'responder', 'status', 'assigned_at')
    list_filter = ('status',)