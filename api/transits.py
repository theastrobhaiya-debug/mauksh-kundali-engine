# api/transits.py
#
# Mauksh Vedic Transit Engine
# Swiss Ephemeris based
#
# Endpoints:
#
# GET /api/planetary-positions
# GET /api/upcoming-transits
# GET /api/transits
#
# Optional:
# datetime=2026-08-27T12:00:00+05:30


from datetime import datetime, timedelta, timezone

import swisseph as swe

from flask import Blueprint, jsonify, request


# ============================================================
# BLUEPRINT
# ============================================================

transits_api = Blueprint(
    "transits_api",
    __name__
)


# ============================================================
# VEDIC SETTINGS
# ============================================================

swe.set_sid_mode(
    swe.SIDM_LAHIRI
)


FLAGS = (
    swe.FLG_SWIEPH
    | swe.FLG_SIDEREAL
    | swe.FLG_SPEED
)


# ============================================================
# RASHIS
# ============================================================

RASHIS = [
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


RASHI_ENGLISH = [
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


# ============================================================
# NAKSHATRAS
# ============================================================

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


# ============================================================
# PLANETS
# ============================================================

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


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize(value):
    return float(value) % 360.0


def get_datetime():

    value = request.args.get(
        "datetime"
    )

    if not value:
        return datetime.now(
            timezone.utc
        )

    value = value.strip()

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    dt = datetime.fromisoformat(
        value
    )

    if dt.tzinfo is None:
        dt = dt.replace(
            tzinfo=timezone.utc
        )

    return dt


def julian_day(dt):

    dt = dt.astimezone(
        timezone.utc
    )

    hour = (
        dt.hour
        + dt.minute / 60
        + dt.second / 3600
        + dt.microsecond / 3600000000
    )

    return swe.julday(
        dt.year,
        dt.month,
        dt.day,
        hour,
        swe.GREG_CAL
    )


# ============================================================
# RASHI
# ============================================================

def get_rashi(longitude):

    longitude = normalize(
        longitude
    )

    index = int(
        longitude / 30.0
    )

    degree = (
        longitude
        - index * 30.0
    )

    return {
        "number": index + 1,
        "name": RASHIS[index],
        "english": RASHI_ENGLISH[index],
        "degree": degree,
    }


# ============================================================
# NAKSHATRA
# ============================================================

def get_nakshatra(longitude):

    longitude = normalize(
        longitude
    )

    nakshatra_size = (
        360.0 / 27.0
    )

    pada_size = (
        nakshatra_size / 4.0
    )

    index = int(
        longitude / nakshatra_size
    )

    position = (
        longitude
        - index * nakshatra_size
    )

    pada = int(
        position / pada_size
    ) + 1

    return {
        "number": index + 1,
        "name": NAKSHATRAS[index],
        "pada": pada,
        "lord": NAKSHATRA_LORDS[
            index % 9
        ],
    }


# ============================================================
# DEGREE FORMAT
# ============================================================

def format_degree(value):

    degrees = int(value)

    minutes_float = (
        value - degrees
    ) * 60

    minutes = int(
        minutes_float
    )

    seconds = round(
        (
            minutes_float
            - minutes
        ) * 60
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


# ============================================================
# PLANET POSITION
# ============================================================

def planet_position(
    planet_name,
    dt
):

    jd = julian_day(
        dt
    )

    planet_id = PLANETS[
        planet_name
    ]

    result, _ = swe.calc_ut(
        jd,
        planet_id,
        FLAGS
    )

    longitude = normalize(
        result[0]
    )

    speed = float(
        result[3]
    )

    rashi = get_rashi(
        longitude
    )

    nakshatra = get_nakshatra(
        longitude
    )

    return {
        "planet":
            planet_name,

        "symbol":
            SYMBOLS[planet_name],

        "longitude":
            round(
                longitude,
                6
            ),

        "rashi":
            rashi["name"],

        "rashi_english":
            rashi["english"],

        "rashi_number":
            rashi["number"],

        "degree":
            round(
                rashi["degree"],
                6
            ),

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
            round(
                speed,
                8
            ),

        "retrograde":
            speed < 0,

        "motion":
            (
                "Retrograde"
                if speed < 0
                else "Direct"
            ),
    }


# ============================================================
# KETU
# ============================================================

def ketu_position(dt):

    rahu = planet_position(
        "Rahu",
        dt
    )

    longitude = normalize(
        rahu["longitude"]
        + 180.0
    )

    rashi = get_rashi(
        longitude
    )

    nakshatra = get_nakshatra(
        longitude
    )

    return {
        "planet":
            "Ketu",

        "symbol":
            "☋",

        "longitude":
            round(
                longitude,
                6
            ),

        "rashi":
            rashi["name"],

        "rashi_english":
            rashi["english"],

        "rashi_number":
            rashi["number"],

        "degree":
            round(
                rashi["degree"],
                6
            ),

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


# ============================================================
# ALL PLANETS
# ============================================================

def all_positions(dt):

    positions = []

    for planet in PLANETS:

        positions.append(
            planet_position(
                planet,
                dt
            )
        )

    positions.append(
        ketu_position(
            dt
        )
    )

    return positions


# ============================================================
# CURRENT PLANETARY POSITIONS API
# ============================================================

@transits_api.route(
    "/api/planetary-positions",
    methods=["GET"]
)
def planetary_positions():

    try:

        dt = get_datetime()

        planets = all_positions(
            dt
        )

        return jsonify({

            "success":
                True,

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

            "planets":
                planets,
        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e),

        }), 500


# ============================================================
# NEXT RASHI TRANSIT
# ============================================================

def next_rashi_transit(
    planet,
    start_dt,
    days=400
):

    current = planet_position(
        planet,
        start_dt
    )

    current_rashi = (
        current["rashi_number"]
    )

    step = timedelta(
        hours=6
    )

    end_dt = (
        start_dt
        + timedelta(
            days=days
        )
    )

    check = (
        start_dt
        + step
    )

    while check <= end_dt:

        position = planet_position(
            planet,
            check
        )

        if (
            position[
                "rashi_number"
            ]
            != current_rashi
        ):

            # Binary search for
            # approximate exact crossing.

            low = (
                check - step
            )

            high = check

            for _ in range(40):

                middle = (
                    low
                    + (
                        high - low
                    ) / 2
                )

                middle_position = (
                    planet_position(
                        planet,
                        middle
                    )
                )

                if (
                    middle_position[
                        "rashi_number"
                    ]
                    == current_rashi
                ):
                    low = middle
                else:
                    high = middle

            final_position = (
                planet_position(
                    planet,
                    high
                )
            )

            return {

                "planet":
                    planet,

                "from_rashi":
                    current["rashi"],

                "from_rashi_english":
                    current[
                        "rashi_english"
                    ],

                "to_rashi":
                    final_position[
                        "rashi"
                    ],

                "to_rashi_english":
                    final_position[
                        "rashi_english"
                    ],

                "transit_utc":
                    high.astimezone(
                        timezone.utc
                    ).isoformat(),

            }

        check += step

    return None


# ============================================================
# UPCOMING TRANSITS API
# ============================================================

@transits_api.route(
    "/api/upcoming-transits",
    methods=["GET"]
)
def upcoming_transits():

    try:

        dt = get_datetime()

        limits = {

            "Sun":
                45,

            "Moon":
                5,

            "Mars":
                150,

            "Mercury":
                120,

            "Jupiter":
                500,

            "Venus":
                120,

            "Saturn":
                1000,

            "Rahu":
                1000,
        }

        transits = []

        for planet, days in limits.items():

            result = next_rashi_transit(
                planet,
                dt,
                days
            )

            if result:

                transits.append(
                    result
                )

        transits.sort(
            key=lambda item:
                item["transit_utc"]
        )

        return jsonify({

            "success":
                True,

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

            "transits":
                transits,

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e),

        }), 500


# ============================================================
# COMBINED API
# ============================================================

@transits_api.route(
    "/api/transits",
    methods=["GET"]
)
def combined_transits():

    try:

        dt = get_datetime()

        return jsonify({

            "success":
                True,

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
                all_positions(dt),

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e),

        }), 500