from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = (
        ('citizen', 'Citizen'),
        ('responder', 'Emergency Responder'),
        ('admin', 'System Admin'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citizen')
    phone_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Location(models.Model):
    name = models.CharField(max_length=150)
    ward = models.CharField(max_length=100, blank=True, help_text="e.g. Bulabulin, Gwange")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.latitude}, {self.longitude})"


class HistoricalFloodRecord(models.Model):
    """Stores a past, confirmed flood event for a location, including the
    water level recorded when that flood occurred. Used by the prediction
    engine to compare a new reading against what has previously caused
    flooding at that specific location."""
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='historical_records')
    flood_date = models.DateField(help_text="Date the historical flood occurred")
    water_level_recorded = models.FloatField(help_text="Water level (0-10 scale) recorded during that flood")
    rainfall_mm_recorded = models.FloatField(blank=True, null=True, help_text="Rainfall (mm) recorded during that flood, if known")
    description = models.TextField(blank=True, help_text="Brief note on the event, e.g. 'Alau Dam spillway collapse'")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-flood_date']

    def __str__(self):
        return f"{self.location.name} flood on {self.flood_date} (level {self.water_level_recorded})"


class FloodReport(models.Model):
    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('resolved', 'Resolved'),
    )
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='flood_reports')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='flood_reports')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to='flood_reports/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location.name} - {self.severity} ({self.reported_at.date()})"


class FloodPrediction(models.Model):
    RISK_CHOICES = (
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('severe', 'Severe Risk'),
    )
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='predictions')
    risk_level = models.CharField(max_length=20, choices=RISK_CHOICES)
    rainfall_mm = models.FloatField(help_text="Recorded/estimated rainfall in mm")
    water_level = models.FloatField(help_text="River/water body level indicator")
    matched_historical_flood = models.ForeignKey(HistoricalFloodRecord, on_delete=models.SET_NULL, null=True, blank=True, help_text="Historical record this prediction matched/exceeded, if any")
    predicted_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.location.name} - {self.risk_level} ({self.predicted_at.date()})"


class Alert(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='alerts')
    prediction = models.ForeignKey(FloodPrediction, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Alert: {self.location.name} - {self.sent_at.date()}"


class EmergencyResponse(models.Model):
    STATUS_CHOICES = (
        ('assigned', 'Assigned'),
        ('en_route', 'En Route'),
        ('on_site', 'On Site'),
        ('completed', 'Completed'),
    )
    flood_report = models.ForeignKey(FloodReport, on_delete=models.CASCADE, related_name='responses')
    responder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_responses')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Response to {self.flood_report} - {self.status}"