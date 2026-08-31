import swisseph as swe

from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, Response
from zoneinfo import ZoneInfo


app = Flask(__name__)


# =========================================================
# CORS
# =========================================================

@app.after_request
def add_cors_headers(response):

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"

    return response


# =========================================================
# EXISTING APIs
# =========================================================

from api.location import location_api
from api.panchang import panchang_api

app.register_blueprint(location_api)
app.register_blueprint(panchang_api)


# =========================================================
# SWISS EPHEMERIS
# =========================================================

swe.set_ephe_path(".")
swe.set_sid_mode(swe.SIDM_LAHIRI)


# =========================================================
# ZODIAC
# =========================================================

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
    "Pisces"
]


# =========================================================
# NAKSHATRAS
# =========================================================

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
    "Revati"
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
    "Mercury"
]

NAKSHATRA_SIZE = 360.0 / 27.0
PADA_SIZE = NAKSHATRA_SIZE / 4.0


# =========================================================
# VIMSHOTTARI DASHA
# =========================================================

DASHA_YEARS = {
    "Ketu": 7,
    "Venus": 20,
    "Sun": 6,
    "Moon": 10,
    "Mars": 7,
    "Rahu": 18,
    "Jupiter": 16,
    "Saturn": 19,
    "Mercury": 17
}

DASHA_SEQUENCE = [
    "Ketu",
    "Venus",
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury"
]


# =========================================================
# PLANETS
# =========================================================

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mars": swe.MARS,
    "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER,
    "Venus": swe.VENUS,
    "Saturn": swe.SATURN,
    "Rahu": swe.MEAN_NODE
}


# =========================================================
# DISPLAY NAMES
# =========================================================

PLANET_ABBREVIATIONS = {
    "Sun": "Su",
    "Moon": "Mo",
    "Mars": "Ma",
    "Mercury": "Me",
    "Jupiter": "Ju",
    "Venus": "Ve",
    "Saturn": "Sa",
    "Rahu": "Ra",
    "Ketu": "Ke"
}


# =========================================================
# BASIC HELPERS
# =========================================================

def normalize_degree(value):

    return value % 360.0


def get_sign(longitude):

    longitude = normalize_degree(longitude)

    sign_index = int(longitude // 30)

    degree = longitude % 30

    return {
        "name": SIGNS[sign_index],
        "number": sign_index + 1,
        "degree": round(degree, 6),
        "longitude": round(longitude, 6)
    }


def decimal_to_dms(decimal_degree):

    decimal_degree = decimal_degree % 30.0

    degrees = int(decimal_degree)

    minutes_float = (
        decimal_degree - degrees
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

    return degrees, minutes, seconds


def format_degree(decimal_degree):

    degrees, minutes, seconds = decimal_to_dms(
        decimal_degree
    )

    return f"{degrees:02d}°{minutes:02d}'"


# =========================================================
# NAKSHATRA
# =========================================================

def get_nakshatra(longitude):

    longitude = normalize_degree(longitude)

    nakshatra_index = int(
        longitude / NAKSHATRA_SIZE
    )

    position = (
        longitude
        - nakshatra_index * NAKSHATRA_SIZE
    )

    pada = int(
        position / PADA_SIZE
    ) + 1

    lord = NAKSHATRA_LORDS[
        nakshatra_index % 9
    ]

    return {
        "name": NAKSHATRAS[nakshatra_index],
        "number": nakshatra_index + 1,
        "pada": pada,
        "lord": lord,
        "degree_in_nakshatra": round(
            position,
            6
        )
    }


# =========================================================
# NAVAMSHA / D9
# =========================================================

def get_navamsa(longitude):

    longitude = normalize_degree(longitude)

    sign_index = int(
        longitude // 30
    )

    degree_in_sign = (
        longitude % 30
    )

    navamsa_number = int(
        degree_in_sign / (30.0 / 9.0)
    )

    # Movable
    if sign_index % 3 == 0:

        start_sign = sign_index

    # Fixed
    elif sign_index % 3 == 1:

        start_sign = (
            sign_index + 8
        ) % 12

    # Dual
    else:

        start_sign = (
            sign_index + 4
        ) % 12

    navamsa_sign = (
        start_sign + navamsa_number
    ) % 12

    return {
        "number": navamsa_number + 1,
        "sign": SIGNS[navamsa_sign],
        "sign_number": navamsa_sign + 1
    }


# =========================================================
# WHOLE SIGN HOUSE
# =========================================================

def get_house_from_lagna(
    longitude,
    lagna_sign_number
):

    sign_index = int(
        normalize_degree(longitude) // 30
    )

    house = (
        sign_index
        - (lagna_sign_number - 1)
    ) % 12 + 1

    return house


# =========================================================
# PLANET CALCULATION
# =========================================================

def calculate_planets(julian_day):

    planets = {}

    for name, planet_id in PLANETS.items():

        position, flags = swe.calc_ut(
            julian_day,
            planet_id,
            swe.FLG_SWIEPH
            | swe.FLG_SPEED
            | swe.FLG_SIDEREAL
        )

        longitude = normalize_degree(
            position[0]
        )

        speed = position[3]

        planets[name] = {
            "longitude": round(
                longitude,
                6
            ),

            "sign": get_sign(
                longitude
            ),

            "nakshatra": get_nakshatra(
                longitude
            ),

            "navamsa": get_navamsa(
                longitude
            ),

            "retrograde": speed < 0
        }

    # =====================================================
    # KETU
    # =====================================================

    rahu_longitude = planets[
        "Rahu"
    ]["longitude"]

    ketu_longitude = normalize_degree(
        rahu_longitude + 180
    )

    planets["Ketu"] = {

        "longitude": round(
            ketu_longitude,
            6
        ),

        "sign": get_sign(
            ketu_longitude
        ),

        "nakshatra": get_nakshatra(
            ketu_longitude
        ),

        "navamsa": get_navamsa(
            ketu_longitude
        ),

        "retrograde": True
    }

    return planets


# =========================================================
# ASCENDANT
# =========================================================

def calculate_ascendant(
    julian_day,
    latitude,
    longitude
):

    cusps, ascmc = swe.houses_ex(
        julian_day,
        latitude,
        longitude,
        b"P"
    )

    tropical_ascendant = ascmc[0]

    ayanamsha = swe.get_ayanamsa_ut(
        julian_day
    )

    sidereal_ascendant = normalize_degree(
        tropical_ascendant
        - ayanamsha
    )

    return {

        "longitude": round(
            sidereal_ascendant,
            6
        ),

        "sign": get_sign(
            sidereal_ascendant
        ),

        "nakshatra": get_nakshatra(
            sidereal_ascendant
        ),

        "navamsa": get_navamsa(
            sidereal_ascendant
        )
    }


# =========================================================
# WHOLE SIGN HOUSES
# =========================================================

def calculate_houses(
    lagna_sign_number
):

    houses = []

    for house_number in range(
        1,
        13
    ):

        sign_index = (
            lagna_sign_number
            - 1
            + house_number
            - 1
        ) % 12

        houses.append({

            "house": house_number,

            "sign": SIGNS[
                sign_index
            ],

            "sign_number":
                sign_index + 1,

            "start_degree":
                sign_index * 30
        })

    return houses


# =========================================================
# VIMSHOTTARI DASHA
# =========================================================

def add_years(
    date,
    years
):

    days = years * 365.2425

    return date + timedelta(
        days=days
    )


def calculate_dasha(
    moon_longitude,
    birth_datetime
):

    nakshatra = get_nakshatra(
        moon_longitude
    )

    birth_lord = nakshatra[
        "lord"
    ]

    birth_lord_index = DASHA_SEQUENCE.index(
        birth_lord
    )

    position_in_nakshatra = (
        moon_longitude
        % NAKSHATRA_SIZE
    )

    fraction_completed = (
        position_in_nakshatra
        / NAKSHATRA_SIZE
    )

    fraction_remaining = (
        1.0
        - fraction_completed
    )

    first_dasha_years = (
        DASHA_YEARS[birth_lord]
    )

    balance_years = (
        first_dasha_years
        * fraction_remaining
    )

    mahadashas = []

    current_date = birth_datetime

    for i in range(9):

        lord_index = (
            birth_lord_index + i
        ) % 9

        lord = DASHA_SEQUENCE[
            lord_index
        ]

        if i == 0:

            duration_years = (
                balance_years
            )

        else:

            duration_years = (
                DASHA_YEARS[lord]
            )

        end_date = add_years(
            current_date,
            duration_years
        )

        mahadasha = {

            "lord": lord,

            "start":
                current_date.isoformat(),

            "end":
                end_date.isoformat(),

            "duration_years":
                round(
                    duration_years,
                    6
                ),

            "antardashas": []
        }

        # =================================================
        # ANTARDASHA
        # =================================================

        maha_years = DASHA_YEARS[lord]

        antardasha_start = current_date

        lord_index = DASHA_SEQUENCE.index(
            lord
        )

        for j in range(9):

            antar_index = (
                lord_index + j
            ) % 9

            antar_lord = DASHA_SEQUENCE[
                antar_index
            ]

            antar_years = (
                maha_years
                * DASHA_YEARS[
                    antar_lord
                ]
                / 120
            )

            antar_end = add_years(
                antardasha_start,
                antar_years
            )

            mahadasha[
                "antardashas"
            ].append({

                "lord":
                    antar_lord,

                "start":
                    antardasha_start.isoformat(),

                "end":
                    antar_end.isoformat(),

                "duration_years":
                    round(
                        antar_years,
                        6
                    )
            })

            antardasha_start = (
                antar_end
            )

        mahadashas.append(
            mahadasha
        )

        current_date = end_date

    return {

        "birth_nakshatra":
            nakshatra,

        "starting_mahadasha":
            birth_lord,

        "balance_years":
            round(
                balance_years,
                6
            ),

        "mahadashas":
            mahadashas
    }


# =========================================================
# KUNDALI CALCULATION CORE
# =========================================================

def calculate_kundali(data):

    date = str(
        data["date"]
    )

    time = str(
        data["time"]
    )

    latitude = float(
        data["latitude"]
    )

    longitude = float(
        data["longitude"]
    )

    timezone_offset = float(
        data["timezone"]
    )

    if latitude < -90 or latitude > 90:

        raise ValueError(
            "Latitude must be between -90 and 90"
        )

    if longitude < -180 or longitude > 180:

        raise ValueError(
            "Longitude must be between -180 and 180"
        )

    if timezone_offset < -14 or timezone_offset > 14:

        raise ValueError(
            "Timezone offset must be between -14 and +14"
        )

    # =====================================================
    # LOCAL BIRTH TIME
    # =====================================================

    local_datetime = datetime.fromisoformat(
        f"{date}T{time}"
    )

    # Supplied timezone is a numeric UTC offset.
    #
    # Example:
    # India = +5.5
    #
    # Make the birth datetime explicitly aware.

    local_datetime = local_datetime.replace(
        tzinfo=timezone(
            timedelta(
                hours=timezone_offset
            )
        )
    )

    utc_datetime = local_datetime.astimezone(
        timezone.utc
    )

    # =====================================================
    # JULIAN DAY
    # =====================================================

    utc_hour = (
        utc_datetime.hour
        + utc_datetime.minute / 60.0
        + utc_datetime.second / 3600.0
        + utc_datetime.microsecond / 3600000000.0
    )

    julian_day = swe.julday(
        utc_datetime.year,
        utc_datetime.month,
        utc_datetime.day,
        utc_hour,
        swe.GREG_CAL
    )

    # =====================================================
    # AYANAMSHA
    # =====================================================

    ayanamsha = swe.get_ayanamsa_ut(
        julian_day
    )

    # =====================================================
    # ASCENDANT
    # =====================================================

    ascendant = calculate_ascendant(
        julian_day,
        latitude,
        longitude
    )

    lagna_sign_number = (
        ascendant[
            "sign"
        ]["number"]
    )

    # =====================================================
    # HOUSES
    # =====================================================

    houses = calculate_houses(
        lagna_sign_number
    )

    # =====================================================
    # PLANETS
    # =====================================================

    planets = calculate_planets(
        julian_day
    )

    # =====================================================
    # HOUSE PLACEMENT
    # =====================================================

    for planet_name in planets:

        planet_sign = planets[
            planet_name
        ]["sign"]["number"]

        house = get_house_from_lagna(
            planets[
                planet_name
            ]["longitude"],
            lagna_sign_number
        )

        planets[
            planet_name
        ]["house"] = house

    # =====================================================
    # DASHA
    # =====================================================

    moon_longitude = planets[
        "Moon"
    ]["longitude"]

    dasha = calculate_dasha(
        moon_longitude,
        local_datetime
    )

    # =====================================================
    # RESULT
    # =====================================================

    return {

        "success": True,

        "engine": {

            "name":
                "Mauksh Kundali Engine",

            "version":
                "0.3.0"

        },

        "calculation": {

            "system":
                "Vedic / Sidereal",

            "ayanamsha":
                "Lahiri",

            "ayanamsha_value":
                round(
                    ayanamsha,
                    8
                ),

            "julian_day":
                julian_day
        },

        "birth": {

            "date":
                date,

            "time":
                time,

            "latitude":
                latitude,

            "longitude":
                longitude,

            "timezone":
                timezone_offset,

            "local_datetime":
                local_datetime.isoformat(),

            "utc_datetime":
                utc_datetime.isoformat()
        },

        "ascendant":
            ascendant,

        "houses":
            houses,

        "planets":
            planets,

        "dasha":
            dasha
    }


# =========================================================
# SVG HELPERS
# =========================================================

def svg_escape(value):

    value = str(value)

    return (
        value
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def svg_text(
    x,
    y,
    text,
    size=18,
    anchor="middle",
    weight="400"
):

    return (
        f'<text x="{x}" y="{y}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}px" '
        f'font-weight="{weight}" '
        f'text-anchor="{anchor}" '
        f'fill="#111111">'
        f'{svg_escape(text)}'
        f'</text>'
    )


def svg_line(
    x1,
    y1,
    x2,
    y2,
    width=2
):

    return (
        f'<line '
        f'x1="{x1}" y1="{y1}" '
        f'x2="{x2}" y2="{y2}" '
        f'stroke="#111111" '
        f'stroke-width="{width}" />'
    )


# =========================================================
# NORTH INDIAN CHART GEOMETRY
# =========================================================

def get_north_indian_house_polygons(
    size
):

    s = size

    # Outer square.
    #
    # House numbering:
    #
    #             1
    #       12          2
    #     11                3
    #    10                  4
    #     9                 5
    #       8             6
    #             7
    #
    # Standard North Indian diamond construction.

    points = {

        "tl": (0, 0),
        "tm": (s / 2, 0),
        "tr": (s, 0),

        "ml": (0, s / 2),
        "c": (s / 2, s / 2),
        "mr": (s, s / 2),

        "bl": (0, s),
        "bm": (s / 2, s),
        "br": (s, s)
    }

    p = points

    houses = {

        1: [
            p["tm"],
            p["ml"],
            p["c"]
        ],

        2: [
            p["tm"],
            p["tr"],
            p["mr"],
            p["c"]
        ],

        3: [
            p["tr"],
            p["br"],
            p["mr"]
        ],

        4: [
            p["mr"],
            p["br"],
            p["bm"],
            p["c"]
        ],

        5: [
            p["bm"],
            p["br"],
            p["bl"],
            p["c"]
        ],

        6: [
            p["bl"],
            p["ml"],
            p["c"]
        ],

        7: [
            p["bm"],
            p["ml"],
            p["c"]
        ],

        8: [
            p["bl"],
            p["br"],
            p["bm"],
            p["c"]
        ],

        9: [
            p["bl"],
            p["ml"],
            p["c"]
        ],

        10: [
            p["ml"],
            p["tl"],
            p["tm"],
            p["c"]
        ],

        11: [
            p["tl"],
            p["tm"],
            p["c"]
        ],

        12: [
            p["tl"],
            p["ml"],
            p["c"]
        ]
    }

    # Correct the geometric North Indian layout.
    #
    # The four corner triangles correspond to:
    # 1 = top
    # 4 = right
    # 7 = bottom
    # 10 = left.
    #
    # Intermediate houses occupy the surrounding
    # quadrilaterals.

    houses = {

        1: [
            p["tm"],
            p["ml"],
            p["c"]
        ],

        2: [
            p["tm"],
            p["tr"],
            p["mr"],
            p["c"]
        ],

        3: [
            p["tr"],
            p["mr"],
            p["c"],
            p["br"]
        ],

        4: [
            p["mr"],
            p["br"],
            p["bm"],
            p["c"]
        ],

        5: [
            p["bm"],
            p["br"],
            p["bl"],
            p["c"]
        ],

        6: [
            p["bl"],
            p["ml"],
            p["c"],
            p["bm"]
        ],

        7: [
            p["bm"],
            p["ml"],
            p["c"]
        ],

        8: [
            p["bl"],
            p["br"],
            p["bm"],
            p["c"]
        ],

        9: [
            p["bl"],
            p["ml"],
            p["c"]
        ],

        10: [
            p["ml"],
            p["tl"],
            p["tm"],
            p["c"]
        ],

        11: [
            p["tl"],
            p["tm"],
            p["c"]
        ],

        12: [
            p["tl"],
            p["ml"],
            p["c"]
        ]
    }

    # Instead of relying on overlapping house polygons,
    # use explicit standard line construction below.

    return houses


# =========================================================
# STANDARD NORTH INDIAN SVG
# =========================================================

def render_north_indian_chart(
    kundali,
    width=1000,
    height=1000
):

    margin = 40

    size = min(
        width,
        height
    ) - 2 * margin

    x0 = (
        width - size
    ) / 2

    y0 = (
        height - size
    ) / 2

    s = size

    x1 = x0
    x2 = x0 + s / 2
    x3 = x0 + s

    y1 = y0
    y2 = y0 + s / 2
    y3 = y0 + s

    elements = []

    # =====================================================
    # SVG HEADER
    # =====================================================

    elements.append(
        f'''
<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}"
     height="{height}"
     viewBox="0 0 {width} {height}">
'''
    )

    elements.append(
        f'<rect width="{width}" height="{height}" fill="white"/>'
    )

    # =====================================================
    # OUTER SQUARE
    # =====================================================

    elements.append(
        f'<rect x="{x1}" y="{y1}" '
        f'width="{s}" height="{s}" '
        f'fill="none" stroke="#111111" '
        f'stroke-width="3"/>'
    )

    # =====================================================
    # MAIN DIAGONALS
    # =====================================================

    elements.append(
        svg_line(
            x1,
            y1,
            x3,
            y3,
            2
        )
    )

    elements.append(
        svg_line(
            x3,
            y1,
            x1,
            y3,
            2
        )
    )

    # =====================================================
    # INNER DIAMOND
    # =====================================================

    elements.append(
        f'<polygon '
        f'points="{x2},{y1} '
        f'{x3},{y2} '
        f'{x2},{y3} '
        f'{x1},{y2}" '
        f'fill="none" '
        f'stroke="#111111" '
        f'stroke-width="2"/>'
    )

    # =====================================================
    # HOUSE CENTER
    # =====================================================

    cx = x2
    cy = y2

    # =====================================================
    # HOUSE LABEL POSITIONS
    # =====================================================

    positions = {

        1: (cx, y1 + s * 0.23),

        2: (
            x0 + s * 0.75,
            y0 + s * 0.12
        ),

        3: (
            x0 + s * 0.82,
            y0 + s * 0.28
        ),

        4: (
            x0 + s * 0.77,
            cy
        ),

        5: (
            x0 + s * 0.82,
            y0 + s * 0.72
        ),

        6: (
            x0 + s * 0.75,
            y0 + s * 0.88
        ),

        7: (
            cx,
            y0 + s * 0.77
        ),

        8: (
            x0 + s * 0.25,
            y0 + s * 0.88
        ),

        9: (
            x0 + s * 0.18,
            y0 + s * 0.72
        ),

        10: (
            x0 + s * 0.23,
            cy
        ),

        11: (
            x0 + s * 0.18,
            y0 + s * 0.28
        ),

        12: (
            x0 + s * 0.25,
            y0 + s * 0.12
        )
    }

    # =====================================================
    # SIGN PER HOUSE
    # =====================================================

    houses = kundali["houses"]

    house_signs = {}

    for house in houses:

        house_signs[
            house["house"]
        ] = house["sign_number"]

    # =====================================================
    # PLANETS BY HOUSE
    # =====================================================

    planets_by_house = {

        house: []

        for house in range(
            1,
            13
        )
    }

    for planet_name, planet in kundali[
        "planets"
    ].items():

        house = planet.get(
            "house"
        )

        if house in planets_by_house:

            planets_by_house[
                house
            ].append(
                (
                    planet_name,
                    planet
                )
            )

    # =====================================================
    # HOUSE CONTENT
    # =====================================================

    for house_number in range(
        1,
        13
    ):

        px, py = positions[
            house_number
        ]

        sign_number = house_signs[
            house_number
        ]

        sign_name = SIGNS[
            sign_number - 1
        ]

        # -------------------------------------------------
        # RASHI NUMBER
        # -------------------------------------------------

        elements.append(
            svg_text(
                px,
                py - 28,
                str(sign_number),
                size=20,
                weight="700"
            )
        )

        # -------------------------------------------------
        # LAGNA
        # -------------------------------------------------

        if house_number == 1:

            elements.append(
                svg_text(
                    px,
                    py + 2,
                    "Lagna",
                    size=17,
                    weight="700"
                )
            )

        # -------------------------------------------------
        # PLANETS
        # -------------------------------------------------

        house_planets = planets_by_house[
            house_number
        ]

        if house_planets:

            base_y = py + 34

            for index, (
                planet_name,
                planet
            ) in enumerate(
                house_planets
            ):

                abbreviation = (
                    PLANET_ABBREVIATIONS[
                        planet_name
                    ]
                )

                retrograde = ""

                if planet.get(
                    "retrograde"
                ):

                    retrograde = " R"

                degree = format_degree(
                    planet[
                        "sign"
                    ]["degree"]
                )

                text = (
                    f"{abbreviation} "
                    f"{degree}"
                    f"{retrograde}"
                )

                elements.append(
                    svg_text(
                        px,
                        base_y
                        + index * 23,
                        text,
                        size=16
                    )
                )

    # =====================================================
    # FOOTER
    # =====================================================

    ascendant_sign = kundali[
        "ascendant"
    ]["sign"]["name"]

    elements.append(
        svg_text(
            width / 2,
            height - 12,
            f"Lagna: {ascendant_sign}  |  "
            f"Vedic / Sidereal  |  Lahiri",
            size=14
        )
    )

    elements.append(
        "</svg>"
    )

    return "".join(
        elements
    )


# =========================================================
# HEALTH
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({

        "status":
            "ok",

        "engine":
            "Mauksh Kundali Engine",

        "version":
            "0.3.0"
    })


# =========================================================
# KUNDALI JSON API
# =========================================================

@app.route(
    "/api/kundali",
    methods=["POST"]
)
def kundali():

    data = request.get_json(
        silent=True
    ) or {}

    required = [
        "date",
        "time",
        "latitude",
        "longitude",
        "timezone"
    ]

    missing = [
        field
        for field in required
        if field not in data
    ]

    if missing:

        return jsonify({

            "success":
                False,

            "error":
                "Missing required fields",

            "fields":
                missing

        }), 400

    try:

        result = calculate_kundali(
            data
        )

        return jsonify(
            result
        )

    except Exception as error:

        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# =========================================================
# KUNDALI SVG API
# =========================================================

@app.route(
    "/api/kundali/chart",
    methods=["POST"]
)
def kundali_chart():

    data = request.get_json(
        silent=True
    ) or {}

    required = [
        "date",
        "time",
        "latitude",
        "longitude",
        "timezone"
    ]

    missing = [
        field
        for field in required
        if field not in data
    ]

    if missing:

        return jsonify({

            "success":
                False,

            "error":
                "Missing required fields",

            "fields":
                missing

        }), 400

    try:

        kundali_data = calculate_kundali(
            data
        )

        svg = render_north_indian_chart(
            kundali_data
        )

        return Response(
            svg,
            mimetype="image/svg+xml"
        )

    except Exception as error:

        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# =========================================================
# KUNDALI SVG JSON API
# =========================================================

@app.route(
    "/api/kundali/chart-data",
    methods=["POST"]
)
def kundali_chart_data():

    data = request.get_json(
        silent=True
    ) or {}

    required = [
        "date",
        "time",
        "latitude",
        "longitude",
        "timezone"
    ]

    missing = [
        field
        for field in required
        if field not in data
    ]

    if missing:

        return jsonify({

            "success":
                False,

            "error":
                "Missing required fields",

            "fields":
                missing

        }), 400

    try:

        kundali_data = calculate_kundali(
            data
        )

        svg = render_north_indian_chart(
            kundali_data
        )

        return jsonify({

            "success":
                True,

            "chart_type":
                "north_indian",

            "format":
                "svg",

            "svg":
                svg,

            "kundali":
                kundali_data
        })

    except Exception as error:

        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500


# =========================================================
# LOCAL DEVELOPMENT
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )