import swisseph as swe
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify


transits_api = Blueprint("transits_api", __name__)


# =========================================================
# VEDIC / SIDEREAL SETTINGS
# =========================================================

swe.set_sid_mode(swe.SIDM_LAHIRI)


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


SIGN_HINDI = {
    "Aries": "Mesha",
    "Taurus": "Vrishabha",
    "Gemini": "Mithuna",
    "Cancer": "Karka",
    "Leo": "Simha",
    "Virgo": "Kanya",
    "Libra": "Tula",
    "Scorpio": "Vrishchika",
    "Sagittarius": "Dhanu",
    "Capricorn": "Makara",
    "Aquarius": "Kumbha",
    "Pisces": "Meena",
}


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


PLANET_SYMBOLS = {
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


NAKSHATRA_SIZE = 360.0 / 27.0
PADA_SIZE = NAKSHATRA_SIZE / 4.0


# =========================================================
# HELPERS
# =========================================================

def normalize(value):
    return value % 360.0


def get_sign(longitude):

    longitude = normalize(longitude)

    index = int(longitude // 30)

    degree = longitude % 30

    return {
        "name": SIGNS[index],
        "vedic_name": SIGN_HINDI[SIGNS[index]],
        "number": index + 1,
        "degree": round(degree, 6),
        "longitude": round(longitude, 6),
    }


def format_degree(degree):

    degree = float(degree)

    d = int(degree)

    minutes_float = (degree - d) * 60

    m = int(minutes_float)

    seconds = round((minutes_float - m) * 60)

    if seconds == 60:
        seconds = 0
        m += 1

    if m == 60:
        m = 0
        d += 1

    return f"{d}° {m:02d}' {seconds:02d}\""


def get_nakshatra(longitude):

    longitude = normalize(longitude)

    index = int(longitude / NAKSHATRA_SIZE)

    position = longitude - (index * NAKSHATRA_SIZE)

    pada = int(position / PADA_SIZE) + 1

    lord = NAKSHATRA_LORDS[index % 9]

    return {
        "name": NAKSHATRAS[index],
        "number": index + 1,
        "pada": pada,
        "lord": lord,
        "degree_in_nakshatra": round(position, 6),
    }


# =========================================================
# JULIAN DAY
# =========================================================

def datetime_to_jd(dt):

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    dt = dt.astimezone(timezone.utc)

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
    )


# =========================================================
# PLANET POSITION
# =========================================================

def calculate_planet(planet_name, dt):

    jd = datetime_to_jd(dt)

    planet_id = PLANETS[planet_name]

    flags = (
        swe.FLG_SWIEPH
        | swe.FLG_SIDEREAL
        | swe.FLG_SPEED
    )

    result, retflags = swe.calc_ut(
        jd,
        planet_id,
        flags,
    )

    longitude = normalize(result[0])

    speed = result[3]

    sign = get_sign(longitude)

    nakshatra = get_nakshatra(longitude)

    retrograde = speed < 0

    return {
        "planet": planet_name,
        "symbol": PLANET_SYMBOLS.get(planet_name),
        "longitude": round(longitude, 6),
        "rashi": sign["name"],
        "vedic_rashi": sign["vedic_name"],
        "rashi_number": sign["number"],
        "degree": round(sign["degree"], 6),
        "degree_formatted": format_degree(sign["degree"]),
        "nakshatra": nakshatra["name"],
        "nakshatra_number": nakshatra["number"],
        "pada": nakshatra["pada"],
        "nakshatra_lord": nakshatra["lord"],
        "retrograde": retrograde,
        "motion": "Retrograde" if retrograde else "Direct",
        "speed": round(speed, 8),
    }


# =========================================================
# KETU
# =========================================================

def calculate_ketu(dt):

    rahu = calculate_planet("Rahu", dt)

    longitude = normalize(
        rahu["longitude"] + 180.0
    )

    sign = get_sign(longitude)

    nakshatra = get_nakshatra(longitude)

    return {
        "planet": "Ketu",
        "symbol": "☋",
        "longitude": round(longitude, 6),
        "rashi": sign["name"],
        "vedic_rashi": sign["vedic_name"],
        "rashi_number": sign["number"],
        "degree": round(sign["degree"], 6),
        "degree_formatted": format_degree(sign["degree"]),
        "nakshatra": nakshatra["name"],
        "nakshatra_number": nakshatra["number"],
        "pada": nakshatra["pada"],
        "nakshatra_lord": nakshatra["lord"],
        "retrograde": True,
        "motion": "Retrograde",
        "speed": rahu["speed"],
    }


# =========================================================
# ALL CURRENT PLANETS
# =========================================================

def calculate_all_positions(dt):

    planets = []

    for name in PLANETS:

        planets.append(
            calculate_planet(
                name,
                dt,
            )
        )

    planets.append(
        calculate_ketu(dt)
    )

    return planets


# =========================================================
# FIND NEXT RASHI TRANSIT
# =========================================================

def find_next_rashi_transit(
    planet_name,
    start_dt,
    max_days=1000,
):

    current = calculate_planet(
        planet_name,
        start_dt,
    )

    current_longitude = current["longitude"]

    current_sign = int(
        current_longitude // 30
    )

    target_sign = (
        current_sign + 1
    ) % 12

    target_longitude = (
        target_sign * 30.0
    )

    # If the planet is already extremely close
    # to the boundary, move to the next boundary.
    if (
        target_longitude
        <= current_longitude
        + 0.000001
    ):
        target_longitude += 360.0

    def longitude_forward(dt):

        position = calculate_planet(
            planet_name,
            dt,
        )["longitude"]

        value = position

        while value < current_longitude:
            value += 360.0

        return value

    low = start_dt

    high = start_dt + timedelta(
        days=3
    )

    target = target_longitude

    # Search for the boundary.
    found = False

    for _ in range(
        int(max_days / 3) + 1
    ):

        value = longitude_forward(high)

        if value >= target:

            found = True
            break

        high += timedelta(
            days=3
        )

        if (
            high
            > start_dt
            + timedelta(days=max_days)
        ):
            break

    if not found:
        return None

    # Binary search for accurate time.
    for _ in range(45):

        middle = (
            low
            + (high - low) / 2
        )

        value = longitude_forward(
            middle
        )

        if value >= target:
            high = middle
        else:
            low = middle

    transit_dt = high

    after = calculate_planet(
        planet_name,
        transit_dt
        + timedelta(seconds=5),
    )

    return {
        "planet": planet_name,
        "from_rashi": current["rashi"],
        "from_vedic_rashi": current["vedic_rashi"],
        "to_rashi": after["rashi"],
        "to_vedic_rashi": after["vedic_rashi"],
        "transit_utc": transit_dt.astimezone(
            timezone.utc
        ).isoformat(),
        "longitude": after["longitude"],
        "nakshatra": after["nakshatra"],
    }


# =========================================================
# CURRENT POSITIONS API
# =========================================================

@transits_api.route(
    "/api/planetary-positions",
    methods=["GET"],
)
def planetary_positions():

    try:

        date_string = request.args.get(
            "datetime"
        )

        if date_string:

            dt = datetime.fromisoformat(
                date_string.replace(
                    "Z",
                    "+00:00"
                )
            )

        else:

            dt = datetime.now(
                timezone.utc
            )

        positions = calculate_all_positions(
            dt
        )

        return jsonify({
            "success": True,
            "calculation": {
                "system": "Vedic Sidereal",
                "ayanamsha": "Lahiri",
                "zodiac": "Nirayana",
                "datetime_utc": dt.astimezone(
                    timezone.utc
                ).isoformat(),
            },
            "planets": positions,
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


# =========================================================
# UPCOMING TRANSITS API
# =========================================================

@transits_api.route(
    "/api/upcoming-transits",
    methods=["GET"],
)
def upcoming_transits():

    try:

        date_string = request.args.get(
            "datetime"
        )

        if date_string:

            dt = datetime.fromisoformat(
                date_string.replace(
                    "Z",
                    "+00:00"
                )
            )

        else:

            dt = datetime.now(
                timezone.utc
            )

        transit_list = []

        for planet in PLANETS:

            result = find_next_rashi_transit(
                planet,
                dt,
            )

            if result:
                transit_list.append(
                    result
                )

        # Nodes use the same calculated
        # astronomical node movement.
        rahu = find_next_rashi_transit(
            "Rahu",
            dt,
        )

        if rahu:

            transit_list.append({
                "planet": "Rahu",
                "from_rashi": rahu[
                    "from_rashi"
                ],
                "from_vedic_rashi": rahu[
                    "from_vedic_rashi"
                ],
                "to_rashi": rahu[
                    "to_rashi"
                ],
                "to_vedic_rashi": rahu[
                    "to_vedic_rashi"
                ],
                "transit_utc": rahu[
                    "transit_utc"
                ],
                "longitude": rahu[
                    "longitude"
                ],
                "nakshatra": rahu[
                    "nakshatra"
                ],
            })

        # Ketu is always opposite Rahu.
        if rahu:

            ketu_longitude = normalize(
                rahu["longitude"] + 180
            )

            ketu_sign = get_sign(
                ketu_longitude
            )

            transit_list.append({
                "planet": "Ketu",
                "from_rashi": SIGN_HINDI.get(
                    SIGNS[
                        (
                            SIGNS.index(
                                rahu[
                                    "from_rashi"
                                ]
                            )
                            + 6
                        ) % 12
                    ]
                ),
                "to_rashi": ketu_sign[
                    "name"
                ],
                "to_vedic_rashi": ketu_sign[
                    "vedic_name"
                ],
                "transit_utc": rahu[
                    "transit_utc"
                ],
                "longitude": ketu_longitude,
                "nakshatra": get_nakshatra(
                    ketu_longitude
                )["name"],
            })

        transit_list.sort(
            key=lambda x:
            x["transit_utc"]
        )

        return jsonify({
            "success": True,
            "calculation": {
                "system": "Vedic Sidereal",
                "ayanamsha": "Lahiri",
                "zodiac": "Nirayana",
                "datetime_utc": dt.astimezone(
                    timezone.utc
                ).isoformat(),
            },
            "transits": transit_list,
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


# =========================================================
# COMBINED API
# =========================================================

@transits_api.route(
    "/api/transits",
    methods=["GET"],
)
def combined_transits():

    try:

        date_string = request.args.get(
            "datetime"
        )

        if date_string:

            dt = datetime.fromisoformat(
                date_string.replace(
                    "Z",
                    "+00:00"
                )
            )

        else:

            dt = datetime.now(
                timezone.utc
            )

        positions = calculate_all_positions(
            dt
        )

        upcoming = []

        for planet in PLANETS:

            result = find_next_rashi_transit(
                planet,
                dt,
            )

            if result:
                upcoming.append(
                    result
                )

        upcoming.sort(
            key=lambda x:
            x["transit_utc"]
        )

        return jsonify({
            "success": True,

            "meta": {
                "system": "Vedic Sidereal",
                "zodiac": "Nirayana",
                "ayanamsha": "Lahiri",
                "datetime_utc": dt.astimezone(
                    timezone.utc
                ).isoformat(),
            },

            "current_positions": positions,

            "upcoming_rashi_transits": upcoming,
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500