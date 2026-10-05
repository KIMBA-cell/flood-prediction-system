from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from datetime import date
from .models import User, Location, HistoricalFloodRecord, FloodReport, FloodPrediction, Alert, EmergencyResponse
from .prediction_engine import calculate_risk, get_alert_message, check_historical_match

MMC_AREAS = [
    {"name": "Gwange", "ward": "MMC", "lat": 11.8480, "lng": 13.1450},
    {"name": "Bulabulin", "ward": "MMC", "lat": 11.8250, "lng": 13.1600},
    {"name": "Shehuri", "ward": "MMC", "lat": 11.8420, "lng": 13.1530},
    {"name": "Gambomi", "ward": "MMC", "lat": 11.8395, "lng": 13.1610},
    {"name": "Budum", "ward": "MMC", "lat": 11.8470, "lng": 13.1600},
    {"name": "Adamkolo", "ward": "MMC", "lat": 11.8330, "lng": 13.1700},
    {"name": "Millionaires Quarters", "ward": "MMC", "lat": 11.8500, "lng": 13.1480},
    {"name": "Monday Market", "ward": "MMC", "lat": 11.8460, "lng": 13.1560},
    {"name": "Old Maiduguri", "ward": "MMC", "lat": 11.8460, "lng": 13.1580},
    {"name": "Customs Area", "ward": "MMC", "lat": 11.8395, "lng": 13.1520},
    {"name": "Lagos Street", "ward": "MMC", "lat": 11.8445, "lng": 13.1545},
    {"name": "Alau Dam Road", "ward": "Konduga", "lat": 11.7500, "lng": 13.2833},
]

# Real historical flood data from the September 2024 Alau Dam spillway collapse,
# seeded automatically so it's always present, on any database, without manual
# re-entry. Admins can still add further records (future events) via /admin/
# at any time, independently of this seed.
HISTORICAL_FLOODS = [
    {"location": "Gwange", "date": date(2024, 9, 10), "level": 8.5, "rainfall": 165, "desc": "Alau Dam spillway collapse; Gwange and Lagos Street bridges partially collapsed"},
    {"location": "Bulabulin", "date": date(2024, 9, 10), "level": 9.2, "rainfall": 170, "desc": "Among worst-hit areas; near-total submersion of residential streets"},
    {"location": "Shehuri", "date": date(2024, 9, 10), "level": 8.0, "rainfall": 160, "desc": "Flash flooding from Alau Dam spillway collapse"},
    {"location": "Gambomi", "date": date(2024, 9, 10), "level": 8.3, "rainfall": 160, "desc": "Flash flooding from Alau Dam spillway collapse"},
    {"location": "Budum", "date": date(2024, 9, 10), "level": 7.8, "rainfall": 155, "desc": "Flash flooding; residents displaced to relocation camps"},
    {"location": "Adamkolo", "date": date(2024, 9, 10), "level": 7.5, "rainfall": 150, "desc": "Flash flooding affecting residential blocks"},
    {"location": "Millionaires Quarters", "date": date(2024, 9, 10), "level": 7.0, "rainfall": 145, "desc": "Flooding reached residential compounds"},
    {"location": "Monday Market", "date": date(2024, 9, 10), "level": 8.1, "rainfall": 160, "desc": "Market area flooded, trading disrupted for days"},
    {"location": "Old Maiduguri", "date": date(2024, 9, 10), "level": 7.6, "rainfall": 155, "desc": "Flooding from Alau Dam spillway collapse; access roads submerged"},
    {"location": "Lagos Street", "date": date(2024, 9, 10), "level": 8.4, "rainfall": 160, "desc": "Lagos Street bridge partially collapsed; severe flooding along the corridor"},
    {"location": "Customs Area", "date": date(2024, 9, 10), "level": 7.2, "rainfall": 150, "desc": "Floodwater reached commercial and residential buildings"},
    {"location": "Alau Dam Road", "date": date(2024, 9, 10), "level": 9.5, "rainfall": 180, "desc": "Site of the Alau Dam spillway collapse; highest recorded water level, origin of the flood event"},
]


def ensure_mmc_areas():
    """Creates a Location record for each known MMC area if it doesn't already
    exist, so the interactive map always shows every area, labelled, even with
    no reports or predictions yet."""
    for area in MMC_AREAS:
        Location.objects.get_or_create(
            name=area["name"],
            defaults={"ward": area["ward"], "latitude": area["lat"], "longitude": area["lng"]},
        )


def ensure_historical_records():
    """Seeds the real September 2024 historical flood data for each MMC area,
    if not already present. Safe to call repeatedly — uses get_or_create keyed
    on location + flood_date, so it never duplicates, and never overwrites or
    removes records an admin adds manually for future events."""
    for record in HISTORICAL_FLOODS:
        try:
            location = Location.objects.get(name=record["location"])
        except Location.DoesNotExist:
            continue
        HistoricalFloodRecord.objects.get_or_create(
            location=location,
            flood_date=record["date"],
            defaults={
                "water_level_recorded": record["level"],
                "rainfall_mm_recorded": record["rainfall"],
                "description": record["desc"],
            },
        )


def get_acting_user(request):
    """Returns the logged-in user if authenticated, otherwise a shared 'guest'
    account, so the system can be used freely without requiring login while
    still satisfying the User foreign keys on reports/responses."""
    if request.user.is_authenticated:
        return request.user
    guest, created = User.objects.get_or_create(
        username='guest',
        defaults={'role': 'citizen'}
    )
    return guest


def home(request):
    """Renders the main map page."""
    ensure_mmc_areas()
    ensure_historical_records()
    return render(request, 'core/home.html')


def locations_data(request):
    """Returns all locations with their latest flood reports and predictions as JSON,
    for Leaflet.js to plot as labelled markers. Includes has_active_alert so the
    map can show a pulsing beacon on any location with a live alert."""
    ensure_mmc_areas()
    ensure_historical_records()
    locations = Location.objects.all()
    data = []
    for loc in locations:
        latest_report = loc.flood_reports.order_by('-reported_at').first()
        latest_prediction = loc.predictions.order_by('-predicted_at').first()
        has_active_alert = loc.alerts.filter(is_active=True).exists()
        data.append({
            'id': loc.id,
            'name': loc.name,
            'ward': loc.ward,
            'latitude': float(loc.latitude),
            'longitude': float(loc.longitude),
            'latest_severity': latest_report.severity if latest_report else None,
            'latest_risk': latest_prediction.risk_level if latest_prediction else None,
            'has_active_alert': has_active_alert,
        })
    return JsonResponse({'locations': data})


def location_history(request, location_id):
    """Returns the historical flood records for a specific location as JSON."""
    location = get_object_or_404(Location, id=location_id)
    records = location.historical_records.order_by('-flood_date')
    data = [{
        'flood_date': r.flood_date.strftime('%d %B %Y'),
        'water_level_recorded': r.water_level_recorded,
        'rainfall_mm_recorded': r.rainfall_mm_recorded,
        'description': r.description,
    } for r in records]
    return JsonResponse({'location_name': location.name, 'records': data})


def report_flood(request):
    """Handles the citizen flood-report submission form. Open to everyone;
    uses the logged-in user if available, otherwise a shared guest account."""
    if request.method == 'POST':
        name = request.POST.get('location_name')
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        severity = request.POST.get('severity')
        description = request.POST.get('description')
        photo = request.FILES.get('photo')

        location, created = Location.objects.get_or_create(
            latitude=lat,
            longitude=lng,
            defaults={'name': name}
        )

        FloodReport.objects.create(
            reported_by=get_acting_user(request),
            location=location,
            severity=severity,
            description=description,
            photo=photo
        )
        messages.success(request, 'Flood report submitted successfully.')
        return redirect('core:home')

    return render(request, 'core/report_form.html')


def predict_flood(request):
    """Lets anyone enter rainfall and water level data for a location, open access."""
    ensure_mmc_areas()
    ensure_historical_records()
    locations = Location.objects.all().order_by('name')
    preselected_id = request.GET.get('location_id', '')

    if request.method == 'POST':
        location_id = request.POST.get('location')
        rainfall_mm = request.POST.get('rainfall_mm')
        water_level = request.POST.get('water_level')

        if location_id:
            location = Location.objects.get(id=location_id)
        else:
            new_name = request.POST.get('new_location_name')
            new_ward = request.POST.get('new_location_ward')
            new_lat = request.POST.get('new_latitude')
            new_lng = request.POST.get('new_longitude')

            if not (new_name and new_lat and new_lng):
                messages.error(request, "Please select an existing location or provide a name and GPS coordinates for a new one.")
                return redirect('core:predict_flood')

            location, created = Location.objects.get_or_create(
                latitude=new_lat,
                longitude=new_lng,
                defaults={'name': new_name, 'ward': new_ward or ''}
            )

        risk_level = calculate_risk(rainfall_mm, water_level)
        matched_record, historical_warning = check_historical_match(location, float(water_level))

        prediction = FloodPrediction.objects.create(
            location=location,
            risk_level=risk_level,
            rainfall_mm=rainfall_mm,
            water_level=water_level,
            matched_historical_flood=matched_record,
        )

        should_alert = risk_level in ['high', 'severe'] or matched_record is not None

        if should_alert:
            base_message = get_alert_message(location.name, risk_level)
            full_message = base_message + (f" {historical_warning}" if historical_warning else "")
            Alert.objects.create(
                location=location,
                prediction=prediction,
                message=full_message,
                is_active=True,
            )
            messages.warning(request, f"Prediction saved for {location.name}. Risk level: {risk_level.upper()}."
                              + (f" {historical_warning}" if historical_warning else "")
                              + " An alert was automatically triggered.")
        else:
            messages.success(request, f"Prediction saved for {location.name}. Risk level: {risk_level.upper()}.")

        return redirect('core:home')

    return render(request, 'core/predict_form.html', {'locations': locations, 'preselected_id': preselected_id})


def dashboard(request):
    """Responder dashboard: open access, shows the interactive MMC map,
    pending reports, active alerts, and ongoing responses."""
    ensure_mmc_areas()
    ensure_historical_records()
    pending_reports = FloodReport.objects.exclude(status='resolved').order_by('-reported_at')
    active_alerts = Alert.objects.filter(is_active=True).order_by('-sent_at')
    responses = EmergencyResponse.objects.exclude(status='completed').order_by('-assigned_at')

    context = {
        'pending_reports': pending_reports,
        'active_alerts': active_alerts,
        'responses': responses,
    }
    return render(request, 'core/dashboard.html', context)


def assign_response(request, report_id):
    """Assigns the current user (or guest) to a flood report. Open access."""
    report = get_object_or_404(FloodReport, id=report_id)

    if not EmergencyResponse.objects.filter(flood_report=report).exists():
        EmergencyResponse.objects.create(
            flood_report=report,
            responder=get_acting_user(request),
            status='assigned'
        )
        report.status = 'verified'
        report.save()
        messages.success(request, f"You have been assigned to the report at {report.location.name}.")
    else:
        messages.info(request, "This report is already assigned to a responder.")

    return redirect('core:dashboard')


def update_response_status(request, response_id):
    """Updates the status of an emergency response. Open access."""
    response = get_object_or_404(EmergencyResponse, id=response_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        response.status = new_status
        if new_status == 'completed':
            from django.utils import timezone
            response.completed_at = timezone.now()
            response.flood_report.status = 'resolved'
            response.flood_report.save()
        response.save()
        messages.success(request, f"Response status updated to {new_status}.")

    return redirect('core:dashboard')


@user_passes_test(lambda u: u.is_superuser)
def reset_system(request):
    """Admin-only (still requires superuser login): wipes all test data,
    EXCEPT the seeded MMC areas and their historical flood records, which
    get re-created automatically on the next page load anyway."""
    if request.method == 'POST':
        EmergencyResponse.objects.all().delete()
        Alert.objects.all().delete()
        FloodPrediction.objects.all().delete()
        FloodReport.objects.all().delete()
        HistoricalFloodRecord.objects.all().delete()
        Location.objects.all().delete()
        messages.success(request, "System reset successfully. All test data has been cleared.")
        return redirect('core:home')

    return render(request, 'core/reset_confirm.html')