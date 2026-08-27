from flask import Blueprint, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

panchang_api = Blueprint("panchang_api", __name__)

# ---------------------------------------------------------
# DATA
# ---------------------------------------------------------

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini",
    "Mrigashira", "Ardra", "Punarvasu", "Pushya",
    "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula",
    "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati"
]

YOGAS = [
    "Vishkumbha", "Priti", "Ayushman", "Saubhagya",
    "Shobhana", "Atiganda", "Sukarma", "Dhriti",
    "Shula", "Ganda", "Vriddhi", "Dhruva",
    "Vyaghata", "Harshana", "Vajra", "Siddhi",
    "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla",
    "Brahma", "Indra", "Vaidhriti"
]

KARANAS = [
    "Bava",
    "Balava",
    "Kaulava",
    "Taitila",
    "Garaja",
    "Vanija",
    "Vishti"
]

VARAS = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday"
]

# ---------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------

def norm(value):
    return value % 360.0


def jd_from_datetime(dt):
    return swe.julday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour +
        dt.minute / 60.0 +
        dt.second / 3600.0
    )


def sidereal_longitude(jd, planet):
    flags = (
        swe.FLG_SWIEPH |
        swe.FLG_SIDEREAL
    )

    result, _ = swe.calc_ut(
        jd,
        planet,
        flags
    )

    return norm(result[0])


def get_sun_moon(jd):
    sun = sidereal_longitude(
        jd,
        swe.SUN
    )

    moon = sidereal_longitude(
        jd,
        swe.MOON
    )

    return sun, moon


# ---------------------------------------------------------
# PANCHANG CALCULATIONS
# ---------------------------------------------------------

def get_tithi(sun, moon):

    difference = norm(
        moon - sun
    )

    index = int(
        difference / 12.0
    )

    names = [
        "Pratipada",
        "Dvitiya",
        "Tritiya",
        "Chaturthi",
        "Panchami",
        "Shashthi",
        "Saptami",
        "Ashtami",
        "Navami",
        "Dashami",
        "Ekadashi",
        "Dwadashi",
        "Trayodashi",
        "Chaturdashi",
        "Purnima"
    ]

    if index == 30:
        name = "Amavasya"
    elif index == 14:
        name = "Purnima"
    elif index < 15:
        name = names[index]
    else:
        name = names[index - 15]

    paksha = (
        "Shukla Paksha"
        if index < 15
        else "Krishna Paksha"
    )

    return name, paksha, index


def get_nakshatra(moon):

    nakshatra_size = 360.0 / 27.0

    index = int(
        moon / nakshatra_size
    )

    remainder = (
        moon -
        index * nakshatra_size
    )

    pada = int(
        remainder /
        (nakshatra_size / 4.0)
    ) + 1

    if pada > 4:
        pada = 4

    return (
        NAKSHATRAS[index],
        pada,
        index
    )


def get_yoga(sun, moon):

    value = norm(
        sun + moon
    )

    yoga_size = 360.0 / 27.0

    index = int(
        value / yoga_size
    )

    return YOGAS[index], index


def get_karana(sun, moon):

    difference = norm(
        moon - sun
    )

    half_tithi = int(
        difference / 6.0
    )

    if half_tithi == 0:
        return "Kimstughna"

    if half_tithi >= 57:

        if half_tithi == 57:
            return "Shakuni"

        if half_tithi == 58:
            return "Chatushpada"

        return "Naga"

    return KARANAS[
        (half_tithi - 1) % 7
    ]


# ---------------------------------------------------------
# JULIAN DATE → DATETIME
# ---------------------------------------------------------

def jd_to_datetime(jd):

    result = swe.jdut1_to_utc(
        jd,
        swe.GREG_CAL
    )

    year = int(result[0])
    month = int(result[1])
    day = int(result[2])

    hour_decimal = float(result[3])

    hour = int(
        hour_decimal
    )

    minute_decimal = (
        hour_decimal - hour
    ) * 60.0

    minute = int(
        minute_decimal
    )

    second = int(
        round(
            (minute_decimal - minute) * 60.0
        )
    )

    if second >= 60:
        second = 0
        minute += 1

    if minute >= 60:
        minute = 0
        hour += 1

    return datetime(
        year,
        month,
        day,
        hour,
        minute,
        second,
        tzinfo=timezone.utc
    )


# ---------------------------------------------------------
# SUNRISE / SUNSET
# ---------------------------------------------------------

def sunrise_sunset(
    date,
    latitude,
    longitude
):

    midnight = datetime(
        date.year,
        date.month,
        date.day,
        tzinfo=timezone.utc
    )

    jd = jd_from_datetime(
        midnight
    )

    location = (
        float(longitude),
        float(latitude),
        0.0
    )

    rise = swe.rise_trans(
        jd,
        swe.SUN,
        swe.CALC_RISE,
        location
    )

    setting = swe.rise_trans(
        jd,
        swe.SUN,
        swe.CALC_SET,
        location
    )

    sunrise_jd = rise[1][0]
    sunset_jd = setting[1][0]

    return (
        jd_to_datetime(
            sunrise_jd
        ),
        jd_to_datetime(
            sunset_jd
        )
    )


# ---------------------------------------------------------
# MOONRISE / MOONSET
# ---------------------------------------------------------

def moonrise_moonset(
    date,
    latitude,
    longitude
):

    midnight = datetime(
        date.year,
        date.month,
        date.day,
        tzinfo=timezone.utc
    )

    jd = jd_from_datetime(
        midnight
    )

    location = (
        float(longitude),
        float(latitude),
        0.0
    )

    try:

        rise = swe.rise_trans(
            jd,
            swe.MOON,
            swe.CALC_RISE,
            location
        )

        moonrise = jd_to_datetime(
            rise[1][0]
        )

    except Exception:

        moonrise = None

    try:

        setting = swe.rise_trans(
            jd,
            swe.MOON,
            swe.CALC_SET,
            location
        )

        moonset = jd_to_datetime(
            setting[1][0]
        )

    except Exception:

        moonset = None

    return moonrise, moonset


# ---------------------------------------------------------
# FORMATTING
# ---------------------------------------------------------

def format_local(
    dt,
    timezone_name
):

    if dt is None:
        return None

    tz = ZoneInfo(
        timezone_name
    )

    local = dt.astimezone(
        tz
    )

    return local.strftime(
        "%I:%M %p"
    ).lstrip("0")


def format_duration(delta):

    if delta is None:
        return None

    total_seconds = int(
        delta.total_seconds()
    )

    hours = total_seconds // 3600

    minutes = (
        total_seconds % 3600
    ) // 60

    return (
        f"{hours}h {minutes}m"
    )


# ---------------------------------------------------------
# BOUNDARY SEARCH
# ---------------------------------------------------------

def find_boundary(
    start,
    end,
    value_function,
    initial_value
):

    step = timedelta(
        minutes=10
    )

    current = start

    previous = initial_value

    while current < end:

        next_time = min(
            current + step,
            end
        )

        value = value_function(
            next_time
        )

        if value != previous:

            low = current
            high = next_time

            for _ in range(25):

                middle = (
                    low +
                    (high - low) / 2
                )

                middle_value = (
                    value_function(
                        middle
                    )
                )

                if middle_value == previous:
                    low = middle
                else:
                    high = middle

            return high

        current = next_time
        previous = value

    return None


# ---------------------------------------------------------
# AYANA / RITU
# ---------------------------------------------------------

def get_ayana(sun_rashi_index):

    if (
        sun_rashi_index >= 9 or
        sun_rashi_index <= 2
    ):
        return "Uttarayana"

    return "Dakshinayana"


def get_ritu(
    month
):

    # Approximate traditional solar-season mapping.
    # The core Panchang calculations remain astronomical.

    if month in [12, 1]:
        return "Shishir"

    if month in [2, 3]:
        return "Vasant"

    if month in [4, 5]:
        return "Grishma"

    if month in [6, 7]:
        return "Varsha"

    if month in [8, 9]:
        return "Sharad"

    return "Hemant"


# ---------------------------------------------------------
# RAHU / YAMAGANDA / GULIKA
# ---------------------------------------------------------

RAHU_SEGMENTS = [
    8, 2, 7, 5, 6, 4, 3
]

YAMAGANDA_SEGMENTS = [
    5, 4, 3, 2, 1, 7, 6
]

GULIKA_SEGMENTS = [
    7, 6, 5, 4, 3, 2, 1
]


def daytime_segment(
    sunrise,
    sunset,
    segment
):

    duration = (
        sunset - sunrise
    )

    segment_length = (
        duration / 8
    )

    start = (
        sunrise +
        segment_length * segment
    )

    end = (
        start +
        segment_length
    )

    return start, end


def get_kaal(
    sunrise,
    sunset,
    weekday
):

    rahu_index = (
        RAHU_SEGMENTS[weekday] - 1
    )

    yamaganda_index = (
        YAMAGANDA_SEGMENTS[weekday] - 1
    )

    gulika_index = (
        GULIKA_SEGMENTS[weekday] - 1
    )

    rahu = daytime_segment(
        sunrise,
        sunset,
        rahu_index
    )

    yamaganda = daytime_segment(
        sunrise,
        sunset,
        yamaganda_index
    )

    gulika = daytime_segment(
        sunrise,
        sunset,
        gulika_index
    )

    return rahu, yamaganda, gulika


# ---------------------------------------------------------
# ABHIJIT
# ---------------------------------------------------------

def get_abhijit(
    sunrise,
    sunset
):

    day_duration = (
        sunset - sunrise
    )

    midpoint = (
        sunrise +
        day_duration / 2
    )

    window = (
        day_duration / 15
    )

    return (
        midpoint - window / 2,
        midpoint + window / 2
    )


# ---------------------------------------------------------
# MAIN CALCULATION
# ---------------------------------------------------------

def calculate_panchang(
    date,
    latitude,
    longitude,
    timezone_name
):

    tz = ZoneInfo(
        timezone_name
    )

    local_midnight = datetime(
        date.year,
        date.month,
        date.day,
        tzinfo=tz
    )

    next_midnight = (
        local_midnight +
        timedelta(days=1)
    )

    day_start_utc = (
        local_midnight
        .astimezone(timezone.utc)
    )

    day_end_utc = (
        next_midnight
        .astimezone(timezone.utc)
    )

    sunrise, sunset = (
        sunrise_sunset(
            date,
            latitude,
            longitude
        )
    )

    moonrise, moonset = (
        moonrise_moonset(
            date,
            latitude,
            longitude
        )
    )

    sun, moon = get_sun_moon(
        jd_from_datetime(
            sunrise
        )
    )

    tithi, paksha, _ = (
        get_tithi(
            sun,
            moon
        )
    )

    nakshatra, pada, _ = (
        get_nakshatra(
            moon
        )
    )

    yoga, _ = get_yoga(
        sun,
        moon
    )

    karana = get_karana(
        sun,
        moon
    )

    sun_rashi_index = int(
        sun / 30
    )

    moon_rashi_index = int(
        moon / 30
    )

    sun_rashi = SIGNS[
        sun_rashi_index
    ]

    moon_rashi = SIGNS[
        moon_rashi_index
    ]

    weekday = date.weekday()

    vara = VARAS[
        (weekday + 1) % 7
    ]

    # ---------------------------------------------
    # TITHI END
    # ---------------------------------------------

    tithi_end = find_boundary(
        sunrise,
        day_end_utc,
        lambda dt:
            get_tithi(
                *get_sun_moon(
                    jd_from_datetime(dt)
                )
            )[0],
        tithi
    )

    # ---------------------------------------------
    # NAKSHATRA END
    # ---------------------------------------------

    nakshatra_end = find_boundary(
        sunrise,
        day_end_utc,
        lambda dt:
            get_nakshatra(
                get_sun_moon(
                    jd_from_datetime(dt)
                )[1]
            )[0],
        nakshatra
    )

    # ---------------------------------------------
    # YOGA END
    # ---------------------------------------------

    yoga_end = find_boundary(
        sunrise,
        day_end_utc,
        lambda dt:
            get_yoga(
                *get_sun_moon(
                    jd_from_datetime(dt)
                )
            )[0],
        yoga
    )

    # ---------------------------------------------
    # DAY / NIGHT
    # ---------------------------------------------

    day_duration = (
        sunset - sunrise
    )

    night_duration = (
        timedelta(days=1) -
        day_duration
    )

    # ---------------------------------------------
    # KAAL
    # ---------------------------------------------

    rahu, yamaganda, gulika = (
        get_kaal(
            sunrise,
            sunset,
            weekday
        )
    )

    abhijit = get_abhijit(
        sunrise,
        sunset
    )

    # ---------------------------------------------
    # SAMVAT
    # ---------------------------------------------

    vikram_samvat = (
        date.year + 57
    )

    shaka_samvat = (
        date.year - 78
    )

    # ---------------------------------------------
    # RESULT
    # ---------------------------------------------

    return {

        "success": True,

        "date":
            date.isoformat(),

        "timezone":
            timezone_name,

        "location": {
            "latitude":
                latitude,
            "longitude":
                longitude
        },

        "sunrise":
            format_local(
                sunrise,
                timezone_name
            ),

        "sunset":
            format_local(
                sunset,
                timezone_name
            ),

        "moonrise":
            format_local(
                moonrise,
                timezone_name
            ),

        "moonset":
            format_local(
                moonset,
                timezone_name
            ),

        "tithi": {
            "name":
                tithi,
            "end":
                format_local(
                    tithi_end,
                    timezone_name
                )
        },

        "vara": {
            "name":
                vara
        },

        "nakshatra": {
            "name":
                nakshatra,
            "pada":
                pada,
            "end":
                format_local(
                    nakshatra_end,
                    timezone_name
                )
        },

        "yoga": {
            "name":
                yoga,
            "end":
                format_local(
                    yoga_end,
                    timezone_name
                )
        },

        "karana": {
            "name":
                karana
        },

        "moonRashi":
            moon_rashi,

        "sunRashi":
            sun_rashi,

        "moonNakshatra":
            nakshatra,

        "paksha":
            paksha,

        "ayana":
            get_ayana(
                sun_rashi_index
            ),

        "ritu":
            get_ritu(
                date.month
            ),

        "dayDuration":
            format_duration(
                day_duration
            ),

        "nightDuration":
            format_duration(
                night_duration
            ),

        "vikramSamvat":
            vikram_samvat,

        "shakaSamvat":
            shaka_samvat,

        "sunDay":
            vara,

        "timings": {

            "rahuKaal":
                format_local(
                    rahu[0],
                    timezone_name
                )
                + " – " +
                format_local(
                    rahu[1],
                    timezone_name
                ),

            "yamaganda":
                format_local(
                    yamaganda[0],
                    timezone_name
                )
                + " – " +
                format_local(
                    yamaganda[1],
                    timezone_name
                ),

            "gulika":
                format_local(
                    gulika[0],
                    timezone_name
                )
                + " – " +
                format_local(
                    gulika[1],
                    timezone_name
                ),

            "abhijit":
                format_local(
                    abhijit[0],
                    timezone_name
                )
                + " – " +
                format_local(
                    abhijit[1],
                    timezone_name
                ),

            "brahma":
                None,

            "durMuhurat":
                None,

            "varjyam":
                None,

            "amritKaal":
                None
        },

        "choghadiya": {

            "day": [],

            "night": []
        },

        "festivals": []
    }


# ---------------------------------------------------------
# API
# ---------------------------------------------------------

@panchang_api.route(
    "/api/panchang",
    methods=["GET"]
)
def panchang():

    try:

        date_string = request.args.get(
            "date"
        )

        latitude = request.args.get(
            "latitude",
            type=float
        )

        longitude = request.args.get(
            "longitude",
            type=float
        )

        timezone_name = request.args.get(
            "timezone",
            "Asia/Kolkata"
        )

        if not date_string:

            return jsonify({
                "success": False,
                "error":
                    "date is required"
            }), 400

        if latitude is None:

            return jsonify({
                "success": False,
                "error":
                    "latitude is required"
            }), 400

        if longitude is None:

            return jsonify({
                "success": False,
                "error":
                    "longitude is required"
            }), 400

        try:

            ZoneInfo(
                timezone_name
            )

        except Exception:

            return jsonify({
                "success": False,
                "error":
                    "Invalid timezone"
            }), 400

        date = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()

        result = calculate_panchang(
            date,
            latitude,
            longitude,
            timezone_name
        )

        return jsonify(
            result
        )

    except Exception as error:

        return jsonify({

            "success": False,

            "error":
                str(error)

        }), 500