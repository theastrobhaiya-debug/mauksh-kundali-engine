import swisseph as swe

from datetime import datetime, timezone
from flask import Blueprint, jsonify, request


# =========================================================
# BLUEPRINT
# =========================================================

transits_api = Blueprint("transits_api", __name__)


# =========================================================
# VEDIC SETTINGS
# =========================================================

swe.set_sid_mode(swe.SIDM_LAHIRI)

FLAGS = (
    swe.FLG_SWIEPH
    | swe.FLG_SIDEREAL
    | swe.FLG_SPEED
)


SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]


VEDIC_SIGNS = [
    "Mesha",
    "Vrishabha",
    "Mithuna",
    "Karka",
    "Simha",
    "Kanya",
    "Tula",
    "Vrishchika",
    "Dhanu",
    "Makara",
    "Kumbha",
    "Meena",
]


NAKSHATRAS = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]


NAKSHATRA_LORDS = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
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


SYMBOLS = {
    "Sun": "☉",
    "Moon": "☽",
    "Mars": "♂",
    "Mercury": "☿",
    "Jupiter": "♃",
    "Venus": "♀",
    "Saturn": "♄",
    "Rahu": "☊",
    "Ketu": "☋",
}


# =========================================================
# HELPERS
# =========================================================

def normalize(value):
    return float(value) % 360.0


def get_datetime():
    value = request.args.get("datetime")

    if not value:
        return datetime.now(timezone.utc)

    value = value.replace("Z", "+00:00")

    dt = datetime.fromisoformat(value)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def to_julian_day(dt):
    dt = dt.astimezone(timezone.utc)

    hour = (
        dt.hour
        + dt.minute / 60.0
        + dt.second / 3600.0
        + dt.microsecond / 3600000000.0
    )

    return swe.julday(
        dt.year,
        dt.month,
        dt.day,
        hour
    )


def get_rashi(longitude):

    longitude = normalize(longitude)

    index = int(longitude // 30)

    degree = longitude % 30

    return {
        "name": SIGNS[index],
        "vedic_name": VEDIC_SIGNS[index],
        "number": index + 1,
        "degree": round(degree, 6),
    }


def get_nakshatra(longitude):

    longitude = normalize(longitude)

    nakshatra_size = 360.0 / 27.0
    pada_size = nakshatra_size / 4.0

    index = int(longitude / nakshatra_size)

    position = longitude - (
        index * nakshatra_size
    )

    pada = int(position / pada_size) + 1

    return {
        "name": NAKSHATRAS[index],
        "number": index + 1,
        "pada": pada,
        "lord": NAKSHATRA_LORDS[index % 9],
    }


def format_degree(degree):

    degrees = int(degree)

    minutes_float = (
        degree - degrees
    ) * 60

    minutes = int(minutes_float)

    seconds = round(
        (minutes_float - minutes) * 60
    )

    if seconds >= 60:
        seconds = 0
        minutes += 1

    if minutes >= 60:
        minutes = 0
        degrees += 1

    return (
        f"{degrees}° "
        f"{minutes:02d}' "
        f"{seconds:02d}\""
    )


# =========================================================
# PLANET CALCULATION
# =========================================================

def calculate_planet(name, dt):

    jd = to_julian_day(dt)

    planet_id = PLANETS[name]

    result, flags = swe.calc_ut(
        jd,
        planet_id,
        FLAGS
    )

    longitude = normalize(result[0])

    speed = float(result[3])

    rashi = get_rashi(longitude)

    nakshatra = get_nakshatra(longitude)

    return {
        "planet": name,
        "symbol": SYMBOLS[name],

        "longitude": round(
            longitude,
            6
        ),

        "rashi": rashi["name"],

        "vedic_rashi": rashi[
            "vedic_name"
        ],

        "rashi_number": rashi[
            "number"
        ],

        "degree": rashi[
            "degree"
        ],

        "degree_formatted":
            format_degree(
                rashi["degree"]
            ),

        "nakshatra":
            nakshatra["name"],

        "nakshatra_number":
            nakshatra["number"],

        "pada":
            nakshatra["pada"],

        "nakshatra_lord":
            nakshatra["lord"],

        "speed":
            round(speed, 8),

        "retrograde":
            speed < 0,

        "motion":
            "Retrograde"
            if speed < 0
            else "Direct",
    }


def calculate_ketu(dt):

    rahu = calculate_planet(
        "Rahu",
        dt
    )

    longitude = normalize(
        rahu["longitude"] + 180.0
    )

    rashi = get_rashi(longitude)

    nakshatra = get_nakshatra(
        longitude
    )

    return {
        "planet": "Ketu",
        "symbol": "☋",

        "longitude":
            round(longitude, 6),

        "rashi":
            rashi["name"],

        "vedic_rashi":
            rashi["vedic_name"],

        "rashi_number":
            rashi["number"],

        "degree":
            rashi["degree"],

        "degree_formatted":
            format_degree(
                rashi["degree"]
            ),

        "nakshatra":
            nakshatra["name"],

        "nakshatra_number":
            nakshatra["number"],

        "pada":
            nakshatra["pada"],

        "nakshatra_lord":
            nakshatra["lord"],

        "speed":
            rahu["speed"],

        "retrograde":
            True,

        "motion":
            "Retrograde",
    }


def calculate_all(dt):

    result = []

    for name in PLANETS:
        result.append(
            calculate_planet(
                name,
                dt
            )
        )

    result.append(
        calculate_ketu(dt)
    )

    return result


# =========================================================
# CURRENT PLANETARY POSITIONS
# =========================================================

@transits_api.route(
    "/api/planetary-positions",
    methods=["GET"]
)
def planetary_positions():

    try:

        dt = get_datetime()

        planets = calculate_all(dt)

        return jsonify({
            "success": True,

            "calculation": {
                "system":
                    "Vedic Sidereal",

                "zodiac":
                    "Nirayana",

                "ayanamsha":
                    "Lahiri",

                "datetime_utc":
                    dt.astimezone(
                        timezone.utc
                    ).isoformat(),
            },

            "planets": planets
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# SIMPLE UPCOMING RASHI TRANSITS
# =========================================================

def find_next_sign_change(
    planet,
    start_dt,
    max_days
):

    current = calculate_planet(
        planet,
        start_dt
    )

    previous_sign = current[
        "rashi_number"
    ]

    step_hours = 6

    total_steps = int(
        (max_days * 24)
        / step_hours
    )

    for i in range(
        1,
        total_steps + 1
    ):

        check_dt = (
            start_dt
            + __import__(
                "datetime"
            ).timedelta(
                hours=i * step_hours
            )
        )

        position = calculate_planet(
            planet,
            check_dt
        )

        if (
            position["rashi_number"]
            != previous_sign
        ):

            return {
                "planet": planet,

                "from_rashi":
                    current["rashi"],

                "from_vedic_rashi":
                    current[
                        "vedic_rashi"
                    ],

                "to_rashi":
                    position["rashi"],

                "to_vedic_rashi":
                    position[
                        "vedic_rashi"
                    ],

                "transit_utc":
                    check_dt.astimezone(
                        timezone.utc
                    ).isoformat(),
            }

    return None


@transits_api.route(
    "/api/upcoming-transits",
    methods=["GET"]
)
def upcoming_transits():

    try:

        dt = get_datetime()

        results = []

        limits = {
            "Sun": 40,
            "Moon": 5,
            "Mars": 120,
            "Mercury": 90,
            "Jupiter": 500,
            "Venus": 90,
            "Saturn": 1000,
            "Rahu": 1000,
        }

        for planet in PLANETS:

            transit = find_next_sign_change(
                planet,
                dt,
                limits[planet]
            )

            if transit:
                results.append(
                    transit
                )

        results.sort(
            key=lambda item:
                item["transit_utc"]
        )

        return jsonify({
            "success": True,

            "calculation": {
                "system":
                    "Vedic Sidereal",

                "zodiac":
                    "Nirayana",

                "ayanamsha":
                    "Lahiri",

                "datetime_utc":
                    dt.astimezone(
                        timezone.utc
                    ).isoformat(),
            },

            "transits": results
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# COMBINED ENDPOINT
# =========================================================

@transits_api.route(
    "/api/transits",
    methods=["GET"]
)
def combined_transits():

    try:

        dt = get_datetime()

        planets = calculate_all(dt)

        return jsonify({
            "success": True,

            "calculation": {
                "system":
                    "Vedic Sidereal",

                "zodiac":
                    "Nirayana",

                "ayanamsha":
                    "Lahiri",

                "datetime_utc":
                    dt.astimezone(
                        timezone.utc
                    ).isoformat(),
            },

            "current_positions":
                planets,

            "message":
                "Current planetary positions loaded successfully."
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
