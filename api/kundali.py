import swisseph as swe

from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, Response


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
# HELPERS
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
# NAVAMSHA
# =========================================================

def get_navamsa(longitude):

    longitude = normalize_degree(longitude)

    sign_index = int(
        longitude // 30
    )

    degree_in_sign = longitude % 30

    navamsa_number = int(
        degree_in_sign / (30.0 / 9.0)
    )

    if sign_index % 3 == 0:

        start_sign = sign_index

    elif sign_index % 3 == 1:

        start_sign = (
            sign_index + 8
        ) % 12

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
# HOUSE FROM LAGNA
# =========================================================

def get_house_from_lagna(
    longitude,
    lagna_sign_number
):

    sign_index = int(
        normalize_degree(longitude) // 30
    )

    return (
        sign_index
        - (lagna_sign_number - 1)
    ) % 12 + 1


# =========================================================
# PLANETS
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

            "longitude":
                round(longitude, 6),

            "sign":
                get_sign(longitude),

            "nakshatra":
                get_nakshatra(longitude),

            "navamsa":
                get_navamsa(longitude),

            "retrograde":
                speed < 0
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

        "longitude":
            round(ketu_longitude, 6),

        "sign":
            get_sign(ketu_longitude),

        "nakshatra":
            get_nakshatra(ketu_longitude),

        "navamsa":
            get_navamsa(ketu_longitude),

        "retrograde":
            True
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
        tropical_ascendant - ayanamsha
    )

    return {

        "longitude":
            round(sidereal_ascendant, 6),

        "sign":
            get_sign(sidereal_ascendant),

        "nakshatra":
            get_nakshatra(sidereal_ascendant),

        "navamsa":
            get_navamsa(sidereal_ascendant)
    }


# =========================================================
# WHOLE SIGN HOUSES
# =========================================================

def calculate_houses(
    lagna_sign_number
):

    houses = []

    for house_number in range(1, 13):

        sign_index = (
            lagna_sign_number
            - 1
            + house_number
            - 1
        ) % 12

        houses.append({

            "house":
                house_number,

            "sign":
                SIGNS[sign_index],

            "sign_number":
                sign_index + 1,

            "start_degree":
                sign_index * 30
        })

    return houses


# =========================================================
# DASHA
# =========================================================

def add_years(date, years):

    return date + timedelta(
        days=years * 365.2425
    )


def calculate_dasha(
    moon_longitude,
    birth_datetime
):

    nakshatra = get_nakshatra(
        moon_longitude
    )

    birth_lord = nakshatra["lord"]

    birth_lord_index = DASHA_SEQUENCE.index(
        birth_lord
    )

    position_in_nakshatra = (
        moon_longitude % NAKSHATRA_SIZE
    )

    fraction_completed = (
        position_in_nakshatra
        / NAKSHATRA_SIZE
    )

    fraction_remaining = (
        1.0 - fraction_completed
    )

    balance_years = (
        DASHA_YEARS[birth_lord]
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

            duration_years = balance_years

        else:

            duration_years = DASHA_YEARS[
                lord
            ]

        end_date = add_years(
            current_date,
            duration_years
        )

        mahadasha = {

            "lord":
                lord,

            "start":
                current_date.isoformat(),

            "end":
                end_date.isoformat(),

            "duration_years":
                round(duration_years, 6),

            "antardashas":
                []
        }

        antardasha_start = current_date

        maha_years = DASHA_YEARS[lord]

        lord_index = DASHA_SEQUENCE.index(lord)

        for j in range(9):

            antar_index = (
                lord_index + j
            ) % 9

            antar_lord = DASHA_SEQUENCE[
                antar_index
            ]

            antar_years = (
                maha_years
                * DASHA_YEARS[antar_lord]
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

            antardasha_start = antar_end

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
            round(balance_years, 6),

        "mahadashas":
            mahadashas
    }


# =========================================================
# COMPLETE KUNDALI CALCULATION
# =========================================================

def calculate_kundali(data):

    date = str(data["date"])
    time = str(data["time"])

    latitude = float(data["latitude"])
    longitude = float(data["longitude"])
    timezone_offset = float(data["timezone"])

    if not -90 <= latitude <= 90:
        raise ValueError(
            "Latitude must be between -90 and 90"
        )

    if not -180 <= longitude <= 180:
        raise ValueError(
            "Longitude must be between -180 and 180"
        )

    if not -14 <= timezone_offset <= 14:
        raise ValueError(
            "Timezone offset must be between -14 and +14"
        )

    # =====================================================
    # LOCAL TIME
    # =====================================================

    local_datetime = datetime.fromisoformat(
        f"{date}T{time}"
    )

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
        + utc_datetime.minute / 60
        + utc_datetime.second / 3600
        + utc_datetime.microsecond / 3600000000
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
        ascendant["sign"]["number"]
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

    for planet_name, planet in planets.items():

        planet["house"] = get_house_from_lagna(
            planet["longitude"],
            lagna_sign_number
        )

    # =====================================================
    # DASHA
    # =====================================================

    dasha = calculate_dasha(
        planets["Moon"]["longitude"],
        local_datetime
    )

    return {

        "success":
            True,

        "engine": {

            "name":
                "Mauksh Kundali Engine",

            "version":
                "0.4.0"
        },

        "calculation": {

            "system":
                "Vedic / Sidereal",

            "ayanamsha":
                "Lahiri",

            "ayanamsha_value":
                round(ayanamsha, 8),

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

    return (
        str(value)
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
        f'<text '
        f'x="{x:.2f}" '
        f'y="{y:.2f}" '
        f'font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}px" '
        f'font-weight="{weight}" '
        f'text-anchor="{anchor}" '
        f'fill="#111111">'
        f'{svg_escape(text)}'
        f'</text>'
    )


def polygon_string(points):

    return " ".join(
        f"{x:.2f},{y:.2f}"
        for x, y in points
    )


def polygon_center(points):

    x = sum(
        point[0]
        for point in points
    ) / len(points)

    y = sum(
        point[1]
        for point in points
    ) / len(points)

    return x, y


# =========================================================
# EXACT NORTH INDIAN HOUSE GEOMETRY
# =========================================================

def north_indian_geometry(
    x,
    y,
    size
):

    # -----------------------------------------------------
    # OUTER SQUARE
    # -----------------------------------------------------

    TL = (x, y)
    T = (x + size / 2, y)
    TR = (x + size, y)

    L = (x, y + size / 2)
    C = (x + size / 2, y + size / 2)
    R = (x + size, y + size / 2)

    BL = (x, y + size)
    B = (x + size / 2, y + size)
    BR = (x + size, y + size)

    # -----------------------------------------------------
    # INTERSECTION POINTS
    #
    # These are created by the diagonal lines and
    # the inner diamond.
    # -----------------------------------------------------

    P = (
        x + size / 4,
        y + size / 4
    )

    Q = (
        x + size * 3 / 4,
        y + size / 4
    )

    R2 = (
        x + size * 3 / 4,
        y + size * 3 / 4
    )

    S = (
        x + size / 4,
        y + size * 3 / 4
    )

    # -----------------------------------------------------
    # FIXED NORTH INDIAN HOUSE CELLS
    # -----------------------------------------------------

    houses = {

        # Top centre
        1: [
            T,
            Q,
            C,
            P
        ],

        # Upper-left small
        2: [
            TL,
            T,
            P
        ],

        # Upper-left large
        3: [
            TL,
            P,
            L
        ],

        # Left centre
        4: [
            L,
            P,
            C,
            S
        ],

        # Lower-left large
        5: [
            L,
            BL,
            S
        ],

        # Lower-left small
        6: [
            BL,
            S,
            B
        ],

        # Bottom centre
        7: [
            S,
            C,
            R2,
            B
        ],

        # Lower-right small
        8: [
            B,
            R2,
            BR
        ],

        # Lower-right large
        9: [
            R2,
            R,
            BR
        ],

        # Right centre
        10: [
            C,
            Q,
            R,
            R2
        ],

        # Upper-right large
        11: [
            Q,
            TR,
            R
        ],

        # Upper-right small
        12: [
            T,
            TR,
            Q
        ]
    }

    return houses


# =========================================================
# HOUSE TEXT POSITIONS
# =========================================================

def house_text_positions(
    geometry
):

    positions = {}

    for house_number, points in geometry.items():

        cx, cy = polygon_center(points)

        positions[
            house_number
        ] = {

            "sign":
                (cx, cy - 18),

            "planet":
                (cx, cy + 15)
        }

    return positions


# =========================================================
# RENDER NORTH INDIAN KUNDALI
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

    x = (
        width - size
    ) / 2

    y = (
        height - size
    ) / 2

    geometry = north_indian_geometry(
        x,
        y,
        size
    )

    text_positions = house_text_positions(
        geometry
    )

    svg = []

    # =====================================================
    # SVG START
    # =====================================================

    svg.append(
        f'''
<svg xmlns="http://www.w3.org/2000/svg"
     width="{width}"
     height="{height}"
     viewBox="0 0 {width} {height}">
'''
    )

    svg.append(
        f'<rect width="{width}" '
        f'height="{height}" '
        f'fill="white"/>'
    )

    # =====================================================
    # OUTER SQUARE
    # =====================================================

    svg.append(
        f'<rect '
        f'x="{x:.2f}" '
        f'y="{y:.2f}" '
        f'width="{size:.2f}" '
        f'height="{size:.2f}" '
        f'fill="none" '
        f'stroke="#333333" '
        f'stroke-width="2.5"/>'
    )

    # =====================================================
    # DIAGONALS
    # =====================================================

    svg.append(
        f'<line '
        f'x1="{x:.2f}" '
        f'y1="{y:.2f}" '
        f'x2="{x + size:.2f}" '
        f'y2="{y + size:.2f}" '
        f'stroke="#333333" '
        f'stroke-width="1.8"/>'
    )

    svg.append(
        f'<line '
        f'x1="{x + size:.2f}" '
        f'y1="{y:.2f}" '
        f'x2="{x:.2f}" '
        f'y2="{y + size:.2f}" '
        f'stroke="#333333" '
        f'stroke-width="1.8"/>'
    )

    # =====================================================
    # INNER DIAMOND
    # =====================================================

    T = (x + size / 2, y)
    R = (x + size, y + size / 2)
    B = (x + size / 2, y + size)
    L = (x, y + size / 2)

    svg.append(
        f'<polygon '
        f'points="{polygon_string([T, R, B, L])}" '
        f'fill="none" '
        f'stroke="#333333" '
        f'stroke-width="1.8"/>'
    )

    # =====================================================
    # HOUSE CONTENT
    # =====================================================

    houses = kundali["houses"]

    planets_by_house = {
        house: []
        for house in range(1, 13)
    }

    for planet_name, planet in kundali[
        "planets"
    ].items():

        house = planet.get("house")

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
    # DRAW EACH HOUSE
    # =====================================================

    for house_number in range(1, 13):

        points = geometry[
            house_number
        ]

        cx, cy = polygon_center(
            points
        )

        sign_number = houses[
            house_number - 1
        ]["sign_number"]

        # -------------------------------------------------
        # RASHI NUMBER
        # -------------------------------------------------

        sign_y = cy - 18

        svg.append(
            svg_text(
                cx,
                sign_y,
                str(sign_number),
                size=18,
                weight="700"
            )
        )

        # -------------------------------------------------
        # ASCENDANT
        # -------------------------------------------------

        if house_number == 1:

            svg.append(
                svg_text(
                    cx,
                    cy + 7,
                    "Asc",
                    size=18,
                    weight="700"
                )
            )

        # -------------------------------------------------
        # PLANETS
        # -------------------------------------------------

        planet_list = planets_by_house[
            house_number
        ]

        if planet_list:

            start_y = (
                cy
                + 38
            )

            for index, (
                planet_name,
                planet
            ) in enumerate(
                planet_list
            ):

                abbreviation = (
                    PLANET_ABBREVIATIONS[
                        planet_name
                    ]
                )

                degree = format_degree(
                    planet[
                        "sign"
                    ]["degree"]
                )

                retrograde = ""

                if planet.get(
                    "retrograde"
                ):
                    retrograde = " R"

                text = (
                    f"{abbreviation} "
                    f"{degree}"
                    f"{retrograde}"
                )

                svg.append(
                    svg_text(
                        cx,
                        start_y
                        + index * 22,
                        text,
                        size=15
                    )
                )

    # =====================================================
    # FOOTER
    # =====================================================

    lagna = kundali[
        "ascendant"
    ]["sign"]["name"]

    svg.append(
        svg_text(
            width / 2,
            height - 12,
            f"Lagna: {lagna} | "
            f"Vedic / Sidereal | Lahiri",
            size=13
        )
    )

    svg.append(
        "</svg>"
    )

    return "".join(svg)


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
            "0.4.0"
    })


# =========================================================
# JSON KUNDALI
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
# SVG KUNDALI
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
# CHART DATA
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
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )