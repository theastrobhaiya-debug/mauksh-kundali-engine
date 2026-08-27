import swisseph as swe
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

swe.set_ephe_path(".")

# Lahiri ayanamsha
swe.set_sid_mode(swe.SIDM_LAHIRI)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE,
}


def normalize_degree(value):
    return value % 360


def get_sign(longitude):

    longitude = normalize_degree(longitude)

    sign_number = int(longitude // 30)
    degree = longitude % 30

    return {
        "name": SIGNS[sign_number],
        "number": sign_number + 1,
        "degree": round(degree, 6),
        "longitude": round(longitude, 6)
    }


def get_house(longitude, ascendant):

    longitude = normalize_degree(longitude)
    ascendant = normalize_degree(ascendant)

    distance = (longitude - ascendant) % 360

    return int(distance // 30) + 1


def calculate_planets(julian_day):

    planets = {}

    for name, planet_id in PLANETS.items():

        position, flags = swe.calc_ut(
            julian_day,
            planet_id,
            swe.FLG_SWIEPH |
            swe.FLG_SPEED |
            swe.FLG_SIDEREAL
        )

        longitude = normalize_degree(position[0])
        speed = position[3]

        planets[name] = {
            "longitude": round(longitude, 6),
            "sign": get_sign(longitude),
            "retrograde": speed < 0
        }

    # Ketu is exactly opposite Rahu
    rahu = planets["Rahu"]["longitude"]

    ketu = normalize_degree(rahu + 180)

    planets["Ketu"] = {
        "longitude": round(ketu, 6),
        "sign": get_sign(ketu),
        "retrograde": True
    }

    return planets


def calculate_ascendant(julian_day, latitude, longitude):

    cusps, ascmc = swe.houses_ex(
        julian_day,
        latitude,
        longitude,
        b'P'
    )

    tropical_ascendant = ascmc[0]

    # Convert tropical Ascendant to sidereal
    ayanamsha = swe.get_ayanamsa_ut(julian_day)

    sidereal_ascendant = normalize_degree(
        tropical_ascendant - ayanamsha
    )

    return {
        "longitude": round(sidereal_ascendant, 6),
        "sign": get_sign(sidereal_ascendant)
    }


def calculate_houses(ascendant):

    houses = []

    asc_longitude = ascendant["longitude"]

    for house_number in range(1, 13):

        cusp = normalize_degree(
            asc_longitude + ((house_number - 1) * 30)
        )

        houses.append({
            "house": house_number,
            "longitude": round(cusp, 6),
            "sign": get_sign(cusp)
        })

    return houses


@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "status": "ok",
        "engine": "Mauksh Kundali Engine"
    })


@app.route("/api/kundali", methods=["POST"])
def kundali():

    data = request.get_json(silent=True) or {}

    required = [
        "date",
        "time",
        "latitude",
        "longitude",
        "timezone"
    ]

    missing = [
        field for field in required
        if field not in data
    ]

    if missing:

        return jsonify({
            "success": False,
            "error": "Missing required fields",
            "fields": missing
        }), 400

    try:

        date = data["date"]
        time = data["time"]

        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
        timezone_offset = float(data["timezone"])

        local_datetime = datetime.fromisoformat(
            f"{date}T{time}"
        )

        # Convert local time to UTC
        utc_timestamp = (
            local_datetime.timestamp()
            - timezone_offset * 3600
        )

        utc_datetime = datetime.fromtimestamp(
            utc_timestamp,
            tz=timezone.utc
        )

        utc_hour = (
            utc_datetime.hour
            + utc_datetime.minute / 60
            + utc_datetime.second / 3600
        )

        julian_day = swe.julday(
            utc_datetime.year,
            utc_datetime.month,
            utc_datetime.day,
            utc_hour
        )

        # Ascendant
        ascendant = calculate_ascendant(
            julian_day,
            latitude,
            longitude
        )

        # Houses
        houses = calculate_houses(
            ascendant
        )

        # Planets
        planets = calculate_planets(
            julian_day
        )

        # Add house placement
        for planet in planets:

            planet_longitude = planets[
                planet
            ]["longitude"]

            planets[planet]["house"] = get_house(
                planet_longitude,
                ascendant["longitude"]
            )

        return jsonify({

            "success": True,

            "engine": {
                "name": "Mauksh Kundali Engine",
                "version": "0.1.0"
            },

            "calculation": {
                "system": "Vedic / Sidereal",
                "ayanamsha": "Lahiri",
                "julian_day": julian_day
            },

            "birth": {
                "date": date,
                "time": time,
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone_offset
            },

            "ascendant": ascendant,

            "houses": houses,

            "planets": planets

        })

    except Exception as error:

        return jsonify({

            "success": False,
            "error": str(error)

        }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
