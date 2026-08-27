from flask import Blueprint, jsonify, request
import swisseph as swe
from datetime import datetime, timezone

transits_api = Blueprint("transits_api", __name__)

swe.set_sid_mode(swe.SIDM_LAHIRI)

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


def get_datetime():
    value = request.args.get("datetime")

    if not value:
        return datetime.now(timezone.utc)

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    dt = datetime.fromisoformat(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def get_julian_day(dt):
    dt = dt.astimezone(timezone.utc)

    hour = (
        dt.hour
        + dt.minute / 60
        + dt.second / 3600
    )

    return swe.julday(
        dt.year,
        dt.month,
        dt.day,
        hour
    )


def calculate_planet(name, planet_id, dt):

    jd = get_julian_day(dt)

    flags = (
        swe.FLG_SWIEPH
        | swe.FLG_SIDEREAL
        | swe.FLG_SPEED
    )

    result, _ = swe.calc_ut(
        jd,
        planet_id,
        flags
    )

    longitude = result[0] % 360
    speed = result[3]

    sign_number = int(longitude // 30)

    sign_degree = longitude % 30

    return {
        "planet": name,
        "longitude": round(longitude, 6),
        "sign": sign_number + 1,
        "degree": round(sign_degree, 6),
        "speed": round(speed, 8),
        "retrograde": speed < 0
    }


@transits_api.route(
    "/api/planetary-positions",
    methods=["GET"]
)
def planetary_positions():

    try:

        dt = get_datetime()

        planets = []

        for name, planet_id in PLANETS.items():

            planets.append(
                calculate_planet(
                    name,
                    planet_id,
                    dt
                )
            )

        # Ketu is always 180° from Rahu
        rahu = next(
            p for p in planets
            if p["planet"] == "Rahu"
        )

        ketu_longitude = (
            rahu["longitude"] + 180
        ) % 360

        planets.append({
            "planet": "Ketu",
            "longitude": round(
                ketu_longitude,
                6
            ),
            "sign": int(
                ketu_longitude // 30
            ) + 1,
            "degree": round(
                ketu_longitude % 30,
                6
            ),
            "speed": rahu["speed"],
            "retrograde": True
        })

        return jsonify({
            "success": True,
            "system": "Vedic Sidereal",
            "ayanamsha": "Lahiri",
            "datetime": dt.isoformat(),
            "planets": planets
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500