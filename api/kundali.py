import swisseph as swe
from datetime import datetime, timezone
from flask import Flask, request, jsonify

app = Flask(__name__)

# ---------------------------------------------------------
# SWISS EPHEMERIS
# ---------------------------------------------------------

swe.set_ephe_path(".")
swe.set_sid_mode(swe.SIDM_LAHIRI)

# ---------------------------------------------------------
# ZODIAC
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# NAKSHATRAS
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# VIMSHOTTARI DASHA
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# PLANETS
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# NAKSHATRA
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# NAVAMSHA / D9
# ---------------------------------------------------------

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

    # Movable signs:
    # Aries, Cancer, Libra, Capricorn
    #
    # Fixed signs:
    # Taurus, Leo, Scorpio, Aquarius
    #
    # Dual signs:
    # Gemini, Virgo, Sagittarius, Pisces

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


# ---------------------------------------------------------
# WHOLE-SIGN HOUSE
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# PLANET CALCULATION
# ---------------------------------------------------------

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

    # -----------------------------------------------------
    # KETU
    # -----------------------------------------------------

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


# ---------------------------------------------------------
# ASCENDANT
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# WHOLE-SIGN HOUSES
# ---------------------------------------------------------

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
            "sign_number": sign_index + 1,
            "start_degree": sign_index * 30
        })

    return houses


# ---------------------------------------------------------
# VIMSHOTTARI DASHA
# ---------------------------------------------------------

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

    # How far Moon has travelled through
    # its birth Nakshatra
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

    # -----------------------------------------------------
    # MAHADASHA
    # -----------------------------------------------------

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

        duration_days = (
            duration_years * 365.2425
        )

        end_timestamp = (
            current_date.timestamp()
            + duration_days * 86400
        )

        end_date = datetime.fromtimestamp(
            end_timestamp,
            tz=current_date.tzinfo
        )

        mahadasha = {
            "lord": lord,
            "start": current_date.isoformat(),
            "end": end_date.isoformat(),
            "duration_years": round(
                duration_years,
                6
            ),
            "antardashas": []
        }

        # -------------------------------------------------
        # ANTARDASHA
        # -------------------------------------------------

        maha_years = DASHA_YEARS[lord]

        maha_days = (
            duration_years
            * 365.2425
        )

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

            antar_days = (
                maha_days
                * DASHA_YEARS[
                    antar_lord
                ]
                / 120
            )

            antar_end_timestamp = (
                antardasha_start.timestamp()
                + antar_days * 86400
            )

            antardasha_end = (
                datetime.fromtimestamp(
                    antar_end_timestamp,
                    tz=antardasha_start.tzinfo
                )
            )

            mahadasha[
                "antardashas"
            ].append({

                "lord": antar_lord,

                "start":
                    antardasha_start.isoformat(),

                "end":
                    antardasha_end.isoformat(),

                "duration_years":
                    round(
                        antar_years,
                        6
                    )
            })

            antardasha_start = (
                antardasha_end
            )

        mahadashas.append(
            mahadasha
        )

        current_date = end_date

    return {
        "birth_nakshatra": nakshatra,
        "starting_mahadasha": birth_lord,
        "balance_years": round(
            balance_years,
            6
        ),
        "mahadashas": mahadashas
    }


# ---------------------------------------------------------
# API HEALTH
# ---------------------------------------------------------

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({

        "status": "ok",

        "engine":
            "Mauksh Kundali Engine",

        "version":
            "0.2.0"

    })


# ---------------------------------------------------------
# KUNDALI API
# ---------------------------------------------------------

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

            "success": False,

            "error":
                "Missing required fields",

            "fields":
                missing

        }), 400

    try:

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

        # -------------------------------------------------
        # LOCAL BIRTH TIME
        # -------------------------------------------------

        local_datetime = datetime.fromisoformat(
            f"{date}T{time}"
        )

        # Treat supplied time as local civil time.
        # Convert it to UTC using the supplied offset.

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

        # -------------------------------------------------
        # JULIAN DAY
        # -------------------------------------------------

        julian_day = swe.julday(
            utc_datetime.year,
            utc_datetime.month,
            utc_datetime.day,
            utc_hour
        )

        # -------------------------------------------------
        # AYANAMSHA
        # -------------------------------------------------

        ayanamsha = swe.get_ayanamsa_ut(
            julian_day
        )

        # -------------------------------------------------
        # ASCENDANT
        # -------------------------------------------------

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

        # -------------------------------------------------
        # HOUSES
        # -------------------------------------------------

        houses = calculate_houses(
            lagna_sign_number
        )

        # -------------------------------------------------
        # PLANETS
        # -------------------------------------------------

        planets = calculate_planets(
            julian_day
        )

        # -------------------------------------------------
        # HOUSE PLACEMENT
        # -------------------------------------------------

        for planet_name in planets:

            planet_sign = planets[
                planet_name
            ]["sign"]["number"]

            house = (
                planet_sign
                - lagna_sign_number
            ) % 12 + 1

            planets[
                planet_name
            ]["house"] = house

        # -------------------------------------------------
        # DASHA
        # -------------------------------------------------

        moon_longitude = planets[
            "Moon"
        ]["longitude"]

        dasha = calculate_dasha(
            moon_longitude,
            local_datetime.replace(
                tzinfo=timezone.utc
            )
        )

        # -------------------------------------------------
        # RESPONSE
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "engine": {

                "name":
                    "Mauksh Kundali Engine",

                "version":
                    "0.2.0"

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
                    timezone_offset

            },

            "ascendant":
                ascendant,

            "houses":
                houses,

            "planets":
                planets,

            "dasha":
                dasha

        })

    except Exception as error:

        return jsonify({

            "success": False,

            "error":
                str(error)

        }), 500


# ---------------------------------------------------------
# LOCAL DEVELOPMENT
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=5000,

        debug=False

    )
