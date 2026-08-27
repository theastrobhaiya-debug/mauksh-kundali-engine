from flask import Blueprint, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import math

panchang_api = Blueprint("panchang_api", __name__)

# ============================================================
# MAUKSH PANCHANG ENGINE
# Swiss Ephemeris + Lahiri Ayanamsha
# ============================================================

SIGNS = [
    "Mesha", "Vrishabha", "Mithuna", "Karka",
    "Simha", "Kanya", "Tula", "Vrishchika",
    "Dhanu", "Makara", "Kumbha", "Meena"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini",
    "Mrigashira", "Ardra", "Punarvasu", "Pushya",
    "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula",
    "Purva Ashadha", "Uttara Ashadha", "Shravana",
    "Dhanishtha", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada",
    "Revati"
]

YOGA_NAMES = [
    "Vishkumbha", "Priti", "Ayushman", "Saubhagya",
    "Shobhana", "Atiganda", "Sukarma", "Dhriti",
    "Shula", "Ganda", "Vriddhi", "Dhruva",
    "Vyaghata", "Harshana", "Vajra", "Siddhi",
    "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla",
    "Brahma", "Indra", "Vaidhriti"
]

TITHI_NAMES = [
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi",
    "Panchami", "Shashthi", "Saptami", "Ashtami",
    "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Purnima"
]

KARANA_MOVING = [
    "Bava", "Balava", "Kaulava",
    "Taitila", "Garaja", "Vanija", "Vishti"
]

WEEKDAYS = [
    "Sunday", "Monday", "Tuesday",
    "Wednesday", "Thursday", "Friday", "Saturday"
]

RAHU_SEGMENTS = [8, 2, 7, 5, 6, 4, 3]
YAMAGANDA_SEGMENTS = [5, 4, 3, 2, 1, 7, 6]
GULIKA_SEGMENTS = [7, 6, 5, 4, 3, 2, 1]

CHOGHADIYA_DAY = {
    0: ["Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg"],
    1: ["Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit"],
    2: ["Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog"],
    3: ["Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh"],
    4: ["Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh"],
    5: ["Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal"],
    6: ["Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal"]
}

CHOGHADIYA_NIGHT = {
    0: ["Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh"],
    1: ["Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Chal"],
    2: ["Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal"],
    3: ["Rog", "Udveg", "Shubh", "Amrit", "Chal", "Kaal", "Labh", "Rog"],
    4: ["Labh", "Kaal", "Chal", "Udveg", "Shubh", "Rog", "Amrit", "Labh"],
    5: ["Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg"],
    6: ["Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit"]
}


# ============================================================
# INITIALIZATION
# ============================================================

swe.set_sid_mode(swe.SIDM_LAHIRI)


# ============================================================
# BASIC ASTRONOMY
# ============================================================

def jd_from_datetime(dt):
    return swe.julday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour +
        dt.minute / 60.0 +
        dt.second / 3600.0 +
        dt.microsecond / 3600000000.0
    )


def norm(x):
    return x % 360.0


def planet_sidereal_longitude(jd, planet):
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

    result, _ = swe.calc_ut(
        jd,
        planet,
        flags
    )

    return norm(result[0])


def sun_moon(jd):
    return (
        planet_sidereal_longitude(jd, swe.SUN),
        planet_sidereal_longitude(jd, swe.MOON)
    )


# ============================================================
# PANCHANGA
# ============================================================

def tithi_data(sun, moon):
    elongation = norm(moon - sun)

    number = int(elongation / 12.0) + 1

    if number > 30:
        number = 30

    if number <= 15:
        name = TITHI_NAMES[number - 1]
        paksha = "Shukla"
    else:
        if number == 30:
            name = "Amavasya"
        else:
            name = TITHI_NAMES[number - 16]

        paksha = "Krishna"

    return {
        "number": number,
        "name": name,
        "paksha": paksha,
        "elongation": elongation
    }


def nakshatra_data(moon):
    size = 360.0 / 27.0

    index = min(
        26,
        int(moon / size)
    )

    inside = moon - index * size

    pada = min(
        4,
        int(inside / (size / 4.0)) + 1
    )

    return {
        "number": index + 1,
        "name": NAKSHATRAS[index],
        "pada": pada
    }


def yoga_data(sun, moon):
    value = norm(sun + moon)

    size = 360.0 / 27.0

    index = min(
        26,
        int(value / size)
    )

    return {
        "number": index + 1,
        "name": YOGA_NAMES[index]
    }


def karana_data(sun, moon):
    elongation = norm(moon - sun)

    half = int(
        elongation / 6.0
    ) + 1

    if half == 1:
        name = "Kimstughna"
    elif half == 58:
        name = "Shakuni"
    elif half == 59:
        name = "Chatushpada"
    elif half == 60:
        name = "Naga"
    else:
        name = KARANA_MOVING[
            (half - 2) % 7
        ]

    return {
        "number": half,
        "name": name
    }


# ============================================================
# SUNRISE / SUNSET / MOONRISE / MOONSET
# ============================================================

def jd_to_datetime(jd):
    y, m, d, hour = swe.jdut1_to_utc(
        jd,
        swe.GREG_CAL
    )

    h = int(hour)

    minute_float = (
        hour - h
    ) * 60.0

    minute = int(
        minute_float
    )

    second = int(
        round(
            (minute_float - minute) * 60
        )
    )

    if second >= 60:
        second = 0
        minute += 1

    if minute >= 60:
        minute = 0
        h += 1

    return datetime(
        int(y),
        int(m),
        int(d),
        h,
        minute,
        second,
        tzinfo=timezone.utc
    )


def rise_set(
    date,
    latitude,
    longitude,
    body,
    event
):
    start = datetime(
        date.year,
        date.month,
        date.day,
        tzinfo=timezone.utc
    )

    jd = jd_from_datetime(start)

    geopos = (
        float(longitude),
        float(latitude),
        0.0
    )

    try:
        result = swe.rise_trans(
            jd,
            body,
            event,
            geopos
        )

        return jd_to_datetime(
            result[1][0]
        )

    except Exception:
        return None


# ============================================================
# TRANSITIONS
# ============================================================

def current_value(dt, function):
    return function(
        jd_from_datetime(dt)
    )


def find_transition(
    start,
    end,
    function,
    initial
):
    step = timedelta(
        minutes=5
    )

    current = start
    previous = initial

    while current < end:

        nxt = min(
            current + step,
            end
        )

        value = current_value(
            nxt,
            function
        )

        if value != previous:

            low = current
            high = nxt

            for _ in range(30):

                middle = (
                    low +
                    (high - low) / 2
                )

                middle_value = current_value(
                    middle,
                    function
                )

                if middle_value == previous:
                    low = middle
                else:
                    high = middle

            return high

        current = nxt
        previous = value

    return None


# ============================================================
# FORMAT
# ============================================================

def local_time(dt, timezone_name):

    if not dt:
        return None

    return dt.astimezone(
        ZoneInfo(timezone_name)
    ).strftime(
        "%I:%M %p"
    ).lstrip("0")


def duration_text(delta):

    if not delta:
        return None

    seconds = int(
        delta.total_seconds()
    )

    hours = seconds // 3600

    minutes = (
        seconds % 3600
    ) // 60

    return f"{hours}h {minutes}m"


def range_text(
    start,
    end,
    timezone_name
):
    if not start or not end:
        return None

    return (
        local_time(
            start,
            timezone_name
        )
        + " – " +
        local_time(
            end,
            timezone_name
        )
    )


# ============================================================
# MUHURTA
# ============================================================

def segment(
    sunrise,
    sunset,
    index
):
    duration = (
        sunset - sunrise
    )

    length = duration / 8

    return (
        sunrise + length * index,
        sunrise + length * (index + 1)
    )


def kaal_data(
    sunrise,
    sunset,
    weekday
):

    rahu = segment(
        sunrise,
        sunset,
        RAHU_SEGMENTS[weekday] - 1
    )

    yamaganda = segment(
        sunrise,
        sunset,
        YAMAGANDA_SEGMENTS[weekday] - 1
    )

    gulika = segment(
        sunrise,
        sunset,
        GULIKA_SEGMENTS[weekday] - 1
    )

    day_length = (
        sunset - sunrise
    )

    abhijit_mid = (
        sunrise +
        day_length / 2
    )

    abhijit_length = (
        day_length / 15
    )

    abhijit = (
        abhijit_mid -
        abhijit_length / 2,
        abhijit_mid +
        abhijit_length / 2
    )

    return {
        "rahuKaal": rahu,
        "yamaganda": yamaganda,
        "gulika": gulika,
        "abhijit": abhijit
    }


def brahma_muhurat(
    sunrise
):
    end = sunrise

    start = sunrise - timedelta(
        minutes=96
    )

    return start, end


# ============================================================
# CHOGHADIYA
# ============================================================

def choghadiya(
    sunrise,
    sunset,
    next_sunrise,
    weekday
):

    result_day = []

    result_night = []

    day_duration = (
        sunset - sunrise
    ) / 8

    for i in range(8):

        start = (
            sunrise +
            day_duration * i
        )

        end = (
            sunrise +
            day_duration * (i + 1)
        )

        result_day.append({
            "name":
                CHOGHADIYA_DAY[weekday][i],
            "start":
                start.isoformat(),
            "end":
                end.isoformat()
        })

    night_duration = (
        next_sunrise - sunset
    ) / 8

    for i in range(8):

        start = (
            sunset +
            night_duration * i
        )

        end = (
            sunset +
            night_duration * (i + 1)
        )

        result_night.append({
            "name":
                CHOGHADIYA_NIGHT[weekday][i],
            "start":
                start.isoformat(),
            "end":
                end.isoformat()
        })

    return {
        "day": result_day,
        "night": result_night
    }


# ============================================================
# SAMVATSARA / RITU / AYANA
# ============================================================

def solar_rashi(longitude):

    index = int(
        longitude / 30
    )

    return {
        "number": index + 1,
        "name": SIGNS[index]
    }


def ayana_from_sun(sun):

    # Sidereal solar longitude.
    # Makara to Mithuna = Uttarayana.
    if sun >= 270 or sun < 90:
        return "Uttarayana"

    return "Dakshinayana"


def ritu_from_sun(sun):

    # Six traditional solar seasons.
    index = int(
        (sun % 360) / 60
    )

    names = [
        "Vasanta",
        "Grishma",
        "Varsha",
        "Sharad",
        "Hemanta",
        "Shishira"
    ]

    return names[index]


# ============================================================
# FESTIVAL / VRAT CORE
# ============================================================

def festival_candidates(
    date,
    tithi,
    sun,
    moon
):

    festivals = []

    tithi_number = tithi["number"]

    paksha = tithi["paksha"]

    solar_rashi = int(
        sun / 30
    )

    # Ekadashi
    if tithi_number in (11, 26):
        festivals.append({
            "name": "Ekadashi",
            "type": "Vrat",
            "tithi": tithi["name"],
            "paksha": paksha,
            "date": date.isoformat()
        })

    # Purnima
    if tithi_number == 15:
        festivals.append({
            "name": "Purnima",
            "type": "Tithi",
            "tithi": "Purnima",
            "paksha": "Shukla",
            "date": date.isoformat()
        })

    # Amavasya
    if tithi_number == 30:
        festivals.append({
            "name": "Amavasya",
            "type": "Tithi",
            "tithi": "Amavasya",
            "paksha": "Krishna",
            "date": date.isoformat()
        })

    # Pradosh
    if tithi_number in (13, 28):
        festivals.append({
            "name": "Pradosh Vrat",
            "type": "Vrat",
            "tithi": tithi["name"],
            "paksha": paksha,
            "date": date.isoformat()
        })

    # Sankashti Chaturthi
    if (
        tithi_number == 19
        and paksha == "Krishna"
    ):
        festivals.append({
            "name": "Sankashti Chaturthi",
            "type": "Vrat",
            "tithi": tithi["name"],
            "paksha": paksha,
            "date": date.isoformat()
        })

    # Monthly Shivaratri
    if (
        tithi_number == 29
        and paksha == "Krishna"
    ):
        festivals.append({
            "name": "Masik Shivaratri",
            "type": "Vrat",
            "tithi": tithi["name"],
            "paksha": paksha,
            "date": date.isoformat()
        })

    return festivals


# ============================================================
# MAIN ENGINE
# ============================================================

def calculate_panchang(
    date,
    latitude,
    longitude,
    timezone_name
):

    tz = ZoneInfo(
        timezone_name
    )

    local_start = datetime(
        date.year,
        date.month,
        date.day,
        tzinfo=tz
    )

    local_next = (
        local_start +
        timedelta(days=1)
    )

    sunrise = rise_set(
        date,
        latitude,
        longitude,
        swe.SUN,
        swe.CALC_RISE
    )

    sunset = rise_set(
        date,
        latitude,
        longitude,
        swe.SUN,
        swe.CALC_SET
    )

    moonrise = rise_set(
        date,
        latitude,
        longitude,
        swe.MOON,
        swe.CALC_RISE
    )

    moonset = rise_set(
        date,
        latitude,
        longitude,
        swe.MOON,
        swe.CALC_SET
    )

    if not sunrise or not sunset:
        raise RuntimeError(
            "Unable to calculate sunrise/sunset"
        )

    next_date = (
        date +
        timedelta(days=1)
    )

    next_sunrise = rise_set(
        next_date,
        latitude,
        longitude,
        swe.SUN,
        swe.CALC_RISE
    )

    sunrise_jd = jd_from_datetime(
        sunrise
    )

    sun, moon = sun_moon(
        sunrise_jd
    )

    tithi = tithi_data(
        sun,
        moon
    )

    nakshatra = nakshatra_data(
        moon
    )

    yoga = yoga_data(
        sun,
        moon
    )

    karana = karana_data(
        sun,
        moon
    )

    weekday = (
        date.weekday() + 1
    ) % 7

    # ------------------------------
    # TRANSITIONS
    # ------------------------------

    day_end = (
        local_next
        .astimezone(timezone.utc)
    )

    tithi_end = find_transition(
        sunrise,
        day_end,
        lambda jd:
            tithi_data(
                *sun_moon(jd)
            )["number"],
        tithi["number"]
    )

    nakshatra_end = find_transition(
        sunrise,
        day_end,
        lambda jd:
            nakshatra_data(
                sun_moon(jd)[1]
            )["number"],
        nakshatra["number"]
    )

    yoga_end = find_transition(
        sunrise,
        day_end,
        lambda jd:
            yoga_data(
                *sun_moon(jd)
            )["number"],
        yoga["number"]
    )

    # ------------------------------
    # MUHURTA
    # ------------------------------

    kaal = kaal_data(
        sunrise,
        sunset,
        weekday
    )

    brahma = brahma_muhurat(
        sunrise
    )

    # ------------------------------
    # CHOGHADIYA
    # ------------------------------

    chog = choghadiya(
        sunrise,
        sunset,
        next_sunrise or (
            sunset +
            timedelta(hours=12)
        ),
        weekday
    )

    # ------------------------------
    # FESTIVALS
    # ------------------------------

    festivals = festival_candidates(
        date,
        tithi,
        sun,
        moon
    )

    # ------------------------------
    # RASHI
    # ------------------------------

    moon_rashi = solar_rashi(
        moon
    )

    sun_rashi = solar_rashi(
        sun
    )

    # ------------------------------
    # DURATIONS
    # ------------------------------

    day_duration = (
        sunset - sunrise
    )

    if next_sunrise:
        night_duration = (
            next_sunrise - sunset
        )
    else:
        night_duration = None

    # ------------------------------
    # RESULT
    # ------------------------------

    return {

        "success": True,

        "engine": "Mauksh Panchang Engine",

        "engineVersion": "2.0",

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
            local_time(
                sunrise,
                timezone_name
            ),

        "sunset":
            local_time(
                sunset,
                timezone_name
            ),

        "moonrise":
            local_time(
                moonrise,
                timezone_name
            ),

        "moonset":
            local_time(
                moonset,
                timezone_name
            ),

        "vara": {
            "name":
                WEEKDAYS[weekday]
        },

        "tithi": {
            "number":
                tithi["number"],
            "name":
                tithi["name"],
            "paksha":
                tithi["paksha"],
            "end":
                local_time(
                    tithi_end,
                    timezone_name
                )
        },

        "nakshatra": {
            "number":
                nakshatra["number"],
            "name":
                nakshatra["name"],
            "pada":
                nakshatra["pada"],
            "end":
                local_time(
                    nakshatra_end,
                    timezone_name
                )
        },

        "yoga": {
            "number":
                yoga["number"],
            "name":
                yoga["name"],
            "end":
                local_time(
                    yoga_end,
                    timezone_name
                )
        },

        "karana": {
            "number":
                karana["number"],
            "name":
                karana["name"]
        },

        "moonRashi":
            moon_rashi["name"],

        "sunRashi":
            sun_rashi["name"],

        "moonNakshatra":
            nakshatra["name"],

        "paksha":
            tithi["paksha"],

        "ayana":
            ayana_from_sun(
                sun
            ),

        "ritu":
            ritu_from_sun(
                sun
            ),

        "dayDuration":
            duration_text(
                day_duration
            ),

        "nightDuration":
            duration_text(
                night_duration
            ),

        "timings": {

            "rahuKaal":
                range_text(
                    kaal["rahuKaal"][0],
                    kaal["rahuKaal"][1],
                    timezone_name
                ),

            "yamaganda":
                range_text(
                    kaal["yamaganda"][0],
                    kaal["yamaganda"][1],
                    timezone_name
                ),

            "gulika":
                range_text(
                    kaal["gulika"][0],
                    kaal["gulika"][1],
                    timezone_name
                ),

            "abhijit":
                range_text(
                    kaal["abhijit"][0],
                    kaal["abhijit"][1],
                    timezone_name
                ),

            "brahma":
                range_text(
                    brahma[0],
                    brahma[1],
                    timezone_name
                ),

            "durMuhurat":
                None,

            "varjyam":
                None,

            "amritKaal":
                None
        },

        "choghadiya":
            chog,

        "festivals":
            festivals,

        "samvat": {

            "vikramSamvat":
                date.year + 57,

            "shakaSamvat":
                date.year - 78
        },

        "vikramSamvat":
            date.year + 57,

        "shakaSamvat":
            date.year - 78
    }


# ============================================================
# API ROUTE
# ============================================================

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

        if not -90 <= latitude <= 90:
            return jsonify({
                "success": False,
                "error":
                    "Invalid latitude"
            }), 400

        if not -180 <= longitude <= 180:
            return jsonify({
                "success": False,
                "error":
                    "Invalid longitude"
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

        try:
            date = datetime.strptime(
                date_string,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            return jsonify({
                "success": False,
                "error":
                    "Invalid date. Use YYYY-MM-DD"
            }), 400

        result = calculate_panchang(
            date,
            latitude,
            longitude,
            timezone_name
        )

        return jsonify(
            result
        )

    except Exception as exc:

        return jsonify({
            "success": False,
            "error":
                str(exc)
        }), 500