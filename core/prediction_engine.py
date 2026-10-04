def calculate_risk(rainfall_mm, water_level):
    """
    Rule-based flood risk calculator.

    rainfall_mm: rainfall recorded/estimated in the last 24 hours (mm)
    water_level: water body/drainage level indicator on a 0-10 scale
                 (0 = normal/dry, 10 = overflowing)

    Returns one of: 'low', 'medium', 'high', 'severe'
    """
    rainfall_mm = float(rainfall_mm)
    water_level = float(water_level)

    if rainfall_mm >= 150 or water_level >= 8:
        return 'severe'
    elif rainfall_mm >= 100 or water_level >= 6:
        return 'high'
    elif rainfall_mm >= 50 or water_level >= 4:
        return 'medium'
    else:
        return 'low'


def get_alert_message(location_name, risk_level):
    """Generates a human-readable alert message based on risk level."""
    messages = {
        'severe': f"🚨 SEVERE FLOOD RISK in {location_name}. Immediate evacuation advised. Avoid the area.",
        'high': f"⚠️ HIGH FLOOD RISK in {location_name}. Residents should prepare to move to higher ground.",
        'medium': f"⚠️ MODERATE flood risk detected in {location_name}. Monitor conditions closely.",
        'low': f"ℹ️ Low flood risk in {location_name}. No immediate action needed.",
    }
    return messages.get(risk_level, f"Flood risk update for {location_name}: {risk_level}")


def check_historical_match(location, current_water_level):
    """
    Compares the current water level reading against this location's
    historical flood records. Returns a tuple:
    (matched_record_or_None, warning_message_or_None)

    A match is triggered if the current level reaches or approaches
    (within 90%) a level that previously caused flooding at this location.
    """
    records = location.historical_records.order_by('-water_level_recorded')
    if not records.exists():
        return None, None

    worst_record = records.first()
    threshold = worst_record.water_level_recorded * 0.9

    if current_water_level >= worst_record.water_level_recorded:
        return worst_record, (
            f"🚨 HISTORICAL MATCH: Current water level ({current_water_level}) has REACHED or EXCEEDED "
            f"the level ({worst_record.water_level_recorded}) that caused flooding here on "
            f"{worst_record.flood_date.strftime('%d %B %Y')}. This location has flooded under these "
            f"exact conditions before."
        )
    elif current_water_level >= threshold:
        return worst_record, (
            f"⚠️ HISTORICAL WARNING: Current water level ({current_water_level}) is approaching the level "
            f"({worst_record.water_level_recorded}) that caused flooding here on "
            f"{worst_record.flood_date.strftime('%d %B %Y')}. Increased risk based on past events at this location."
        )
    return None, None