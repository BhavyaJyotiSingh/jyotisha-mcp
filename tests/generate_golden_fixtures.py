import os
import json
import random
from datetime import datetime, timedelta, timezone
from jyotisha.engines.chart import ChartEngine

def main():
    chart_engine = ChartEngine()
    golden_dir = os.path.join("tests", "golden_charts")
    os.makedirs(golden_dir, exist_ok=True)

    # 1. Celebrity/Historical figures (10 charts)
    celebrities = [
        {"name": "Mahatma Gandhi", "datetime_str": "1869-10-02T07:11:00", "lat": 21.6422, "lon": 69.6093},
        {"name": "Albert Einstein", "datetime_str": "1879-03-14T11:30:00", "lat": 48.3984, "lon": 9.9915},
        {"name": "Steve Jobs", "datetime_str": "1955-02-24T19:15:00", "lat": 37.7749, "lon": -122.4194},
        {"name": "Bill Gates", "datetime_str": "1955-10-28T22:00:00", "lat": 47.6062, "lon": -122.3321},
        {"name": "Marie Curie", "datetime_str": "1867-11-07T12:00:00", "lat": 52.2297, "lon": 21.0122},
        {"name": "Isaac Newton", "datetime_str": "1643-01-04T00:00:00", "lat": 52.8086, "lon": -0.6272},
        {"name": "Charles Darwin", "datetime_str": "1809-02-12T12:00:00", "lat": 52.7073, "lon": -2.7553},
        {"name": "Abraham Lincoln", "datetime_str": "1809-02-12T07:00:00", "lat": 37.5878, "lon": -85.7322},
        {"name": "Leonardo da Vinci", "datetime_str": "1452-04-15T22:00:00", "lat": 43.7846, "lon": 10.9255},
        {"name": "Wolfgang Amadeus Mozart", "datetime_str": "1756-01-27T20:00:00", "lat": 47.8095, "lon": 13.0550}
    ]

    count = 0
    for celeb in celebrities:
        try:
            chart = chart_engine.generate_birth_chart(
                datetime_str=celeb["datetime_str"],
                latitude=celeb["lat"],
                longitude=celeb["lon"],
                location_name=celeb["name"]
            )
            expected_planets = {}
            for p in chart.planets:
                expected_planets[p.name] = p.sign

            fixture = {
                "name": celeb["name"],
                "datetime_str": celeb["datetime_str"],
                "latitude": celeb["lat"],
                "longitude": celeb["lon"],
                "expected_ascendant": chart.ascendant.sign,
                "expected_planets": expected_planets
            }
            
            filename = f"celeb_{celeb['name'].lower().replace(' ', '_')}.json"
            with open(os.path.join(golden_dir, filename), "w", encoding="utf-8") as f:
                json.dump(fixture, f, indent=2)
            count += 1
        except Exception as e:
            print(f"Error generating celeb {celeb['name']}: {e}")

    # 2. Historical dates (pre-1900, pre-1582) (30 charts)
    # Generate dates around significant calendar switches and historical years
    historical_dates = []
    # Around Gregorian switch: Oct 1582
    historical_dates.append(("1582-10-04T12:00:00", 41.9028, 12.4964, "rome_pre_gregorian")) # Last Julian day in Rome
    historical_dates.append(("1582-10-15T12:00:00", 41.9028, 12.4964, "rome_post_gregorian")) # First Gregorian day in Rome
    # Various other years
    random.seed(42)
    for year in [500, 800, 1000, 1200, 1400, 1500, 1600, 1700, 1750, 1800, 1850, 1880]:
        for month in [3, 6, 9, 12]:
            day = random.randint(1, 28)
            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            dt_str = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00"
            lat = random.uniform(-40, 60)
            lon = random.uniform(-120, 120)
            historical_dates.append((dt_str, lat, lon, f"hist_{year}_{month}"))

    for dt_str, lat, lon, label in historical_dates:
        try:
            chart = chart_engine.generate_birth_chart(
                datetime_str=dt_str,
                latitude=lat,
                longitude=lon,
                location_name=label
            )
            expected_planets = {}
            for p in chart.planets:
                expected_planets[p.name] = p.sign

            fixture = {
                "name": label,
                "datetime_str": dt_str,
                "latitude": lat,
                "longitude": lon,
                "expected_ascendant": chart.ascendant.sign,
                "expected_planets": expected_planets
            }
            
            filename = f"{label}.json"
            with open(os.path.join(golden_dir, filename), "w", encoding="utf-8") as f:
                json.dump(fixture, f, indent=2)
            count += 1
        except Exception as e:
            print(f"Error generating historical {label}: {e}")

    # 3. Polar edge cases (latitudes > 66.5 or < -66.5) (20 charts)
    polar_cases = []
    for lat in [68.0, 72.0, 80.0, -68.0, -75.0]:
        for month in [6, 12]: # Solstices, where polar night/day happens
            for lon in [0.0, 90.0]:
                dt_str = f"2024-{month:02d}-21T12:00:00"
                label = f"polar_lat_{int(lat)}_lon_{int(lon)}_m_{month}"
                polar_cases.append((dt_str, lat, lon, label))

    for dt_str, lat, lon, label in polar_cases:
        try:
            chart = chart_engine.generate_birth_chart(
                datetime_str=dt_str,
                latitude=lat,
                longitude=lon,
                location_name=label
            )
            expected_planets = {}
            for p in chart.planets:
                expected_planets[p.name] = p.sign

            fixture = {
                "name": label,
                "datetime_str": dt_str,
                "latitude": lat,
                "longitude": lon,
                "expected_ascendant": chart.ascendant.sign,
                "expected_planets": expected_planets
            }
            
            filename = f"{label}.json"
            with open(os.path.join(golden_dir, filename), "w", encoding="utf-8") as f:
                json.dump(fixture, f, indent=2)
            count += 1
        except Exception as e:
            print(f"Error generating polar {label}: {e}")

    # 4. Standard validation/Leap Year/Equinox/Solstice charts (40 charts)
    std_cases = []
    # Solstices/Equinoxes
    for year in [2000, 2012, 2024, 2028]:
        std_cases.append((f"{year}-03-20T12:00:00", 28.6139, 77.2090, f"equinox_vernal_{year}"))
        std_cases.append((f"{year}-06-21T12:00:00", 28.6139, 77.2090, f"solstice_summer_{year}"))
        std_cases.append((f"{year}-09-22T12:00:00", 28.6139, 77.2090, f"equinox_autumnal_{year}"))
        std_cases.append((f"{year}-12-21T12:00:00", 28.6139, 77.2090, f"solstice_winter_{year}"))
        # Leap days
        std_cases.append((f"{year}-02-29T12:00:00", 28.6139, 77.2090, f"leap_day_{year}"))
        std_cases.append((f"{year}-02-29T23:59:59", 28.6139, 77.2090, f"leap_day_end_{year}"))

    # Random modern charts
    for i in range(16):
        year = random.randint(1900, 2025)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        dt_str = f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00"
        lat = random.uniform(-60, 60)
        lon = random.uniform(-180, 180)
        std_cases.append((dt_str, lat, lon, f"rand_modern_{i}"))

    for dt_str, lat, lon, label in std_cases:
        try:
            chart = chart_engine.generate_birth_chart(
                datetime_str=dt_str,
                latitude=lat,
                longitude=lon,
                location_name=label
            )
            expected_planets = {}
            for p in chart.planets:
                expected_planets[p.name] = p.sign

            fixture = {
                "name": label,
                "datetime_str": dt_str,
                "latitude": lat,
                "longitude": lon,
                "expected_ascendant": chart.ascendant.sign,
                "expected_planets": expected_planets
            }
            
            filename = f"{label}.json"
            with open(os.path.join(golden_dir, filename), "w", encoding="utf-8") as f:
                json.dump(fixture, f, indent=2)
            count += 1
        except Exception as e:
            print(f"Error generating standard {label}: {e}")

    print(f"Generated {count} golden charts.")

if __name__ == "__main__":
    main()
