import swisseph as swe
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

# Swiss Ephemeris
swe.set_ephe_path(".")

ZODIAC_SIGNS = [
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


def sign_from_longitude(longitude):
    longitude = longitude % 360
    sign_index = int(longitude // 30)
    degree = longitude % 30

    return {
        "sign": ZODIAC_SIGNS[sign_index],
        "sign_number": sign_index + 1,
        "degree": round(degree, 6),
        "longitude": round(longitude, 6)
    }


def calculate_planets(julian_day):
    planets = {}

    for name, planet_id in PLANETS.items():
        position, flags = swe.calc_ut(
            julian_day,
            planet_id,
            swe.FLG_SWIEPH | swe.FLG_SPEED
        )

        longitude = position[0]
        speed = position[3]

        planets[name] = {
            "longitude": round(longitude, 6),
            "sign": sign_from_longitude(longitude),
            "retrograde": speed < 0
        }

    # Ketu is always opposite Rahu
    rahu_longitude = planets["Rahu"]["longitude"]
    ketu_longitude = (rahu_longitude + 180) % 360

    planets["Ketu"] = {
        "longitude": round(ketu_longitude, 6),
        "sign": sign_from_longitude(ketu_longitude),
        "retrograde": True
    }

    return planets


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

    missing = [field for field in required if field not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "fields": missing
        }), 400

    try:
        date = data["date"]
        time = data["time"]
        timezone_offset = float(data["timezone"])

        local_datetime = datetime.fromisoformat(
            f"{date}T{time}"
        )

        # Convert local time to UTC
        utc_datetime = local_datetime.timestamp() - (
            timezone_offset * 3600
        )

        utc_datetime = datetime.fromtimestamp(
            utc_datetime,
            tz=timezone.utc
        )

        hour = (
            utc_datetime.hour
            + utc_datetime.minute / 60
            + utc_datetime.second / 3600
        )

        julian_day = swe.julday(
            utc_datetime.year,
            utc_datetime.month,
            utc_datetime.day,
            hour
        )

        planets = calculate_planets(julian_day)

        return jsonify({
            "success": True,
            "engine": "Mauksh Kundali Engine",
            "calculation": {
                "julian_day": julian_day,
                "ayanamsha": "Lahiri"
            },
            "birth": {
                "date": date,
                "time": time,
                "latitude": data["latitude"],
                "longitude": data["longitude"],
                "timezone": timezone_offset
            },
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
