# api/panchang.py
#
# Mauksh Panchang Engine
# Swiss Ephemeris based Vedic Panchang calculations
#
# API:
# GET /api/panchang
#
# Required:
#   date=YYYY-MM-DD
#   latitude=<decimal>
#   longitude=<decimal>
#
# Optional:
#   timezone=Asia/Kolkata
#
# Example:
# /api/panchang?date=2026-08-27&latitude=30.1086537&longitude=78.291&timezone=Asia/Kolkata

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import math

import swisseph as swe
from flask import Blueprint, jsonify, request


# ============================================================
# BLUEPRINT
# ============================================================

panchang_api = Blueprint("panchang_api", __name__)


# ============================================================
# SWISS EPHEMERIS
# ============================================================

swe.set_sid_mode(swe.SIDM_LAHIRI)


# ============================================================
# CONSTANTS
# ============================================================

TITHIS = [
    "Pratipada",
    "Dwitiya",
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
    "Purnima",
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
    "Dhanishtha",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

YOGAS = [
    "Vishkambha",
    "Priti",
    "Ayushman",
    "Saubhagya",
    "Shobhana",
    "Atiganda",
    "Sukarma",
    "Dhriti",
    "Shula",
    "Ganda",
    "Vriddhi",
    "Dhruva",
    "Vyaghata",
    "Harshana",
    "Vajra",
    "Siddhi",
    "Vyatipata",
    "Variyana",
    "Parigha",
    "Shiva",
    "Siddha",
    "Sadhya",
    "Shubha",
    "Shukla",
    "Brahma",
    "Indra",
    "Vaidhriti",
]

KARANAS_MOVABLE = [
    "Bava",
    "Balava",
    "Kaulava",
    "Taitila",
    "Garaja",
    "Vanija",
    "Vishti",
]

SIGNS = [
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

WEEKDAYS = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
]

# Rahu Kalam segment index.
RAHU = {
    0: 8,  # Sunday
    1: 2,
    2: 7,
    3: 5,
    4: 6,
    5: 4,
    6: 3,
}

# Yamaganda segment index.
YAMAGANDA = {
    0: 5,
    1: 4,
    2: 3,
    3: 2,
    4: 1,
    5: 7,
    6: 6,
}

# Gulika segment index.
GULIKA = {
    0: 7,
    1: 6,
    2: 5,
    3: 4,
    4: 3,
    5: 2,
    6: 1,
}


# Choghadiya day sequences.
CHOG_DAY = {
    0: ["Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg"],
    1: ["Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit"],
    2: ["Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog"],
    3: ["Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh"],
    4: ["Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh"],
    5: ["Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal"],
    6: ["Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal"],
}

CHOG_NIGHT = {
    0: ["Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh"],
    1: ["Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Chal"],
    2: ["Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal"],
    3: ["Rog", "Udveg", "Shubh", "Amrit", "Chal", "Kaal", "Labh", "Rog"],
    4: ["Labh", "Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh"],
    5: ["Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit"],
    6: ["Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg"],
}


# ============================================================
# BASIC MATH
# ============================================================

def normalize(value):
    return value % 360.0


def jd_from_datetime(dt):
    """
    Convert aware UTC datetime to Julian Day.
    """
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
        swe.GREG_CAL,
    )


def datetime_from_jd(jd):
    """
    Convert Julian Day to UTC datetime.
    """
    year, month, day, hour = swe.revjul(
        jd,
        swe.GREG_CAL,
    )

    hour_int = int(hour)
    minute_float = (hour - hour_int) * 60
    minute = int(minute_float)
    second_float = (minute_float - minute) * 60
    second = int(second_float)

    microsecond = int(
        round((second_float - second) * 1_000_000)
    )

    if microsecond >= 1_000_000:
        second += 1
        microsecond -= 1_000_000

    return datetime(
        year,
        month,
        day,
        hour_int,
        minute,
        second,
        microsecond,
        tzinfo=timezone.utc,
    )


# ============================================================
# PLANETARY POSITIONS
# ============================================================

def sidereal_position(jd, planet):
    """
    Return Lahiri sidereal longitude.
    """
    result, _ = swe.calc_ut(
        jd,
        planet,
        swe.FLG_SWIEPH
        | swe.FLG_SIDEREAL
        | swe.FLG_SPEED,
    )

    return normalize(result[0])


def sun_moon(jd):
    sun = sidereal_position(jd, swe.SUN)
    moon = sidereal_position(jd, swe.MOON)

    return sun, moon


# ============================================================
# SUNRISE / SUNSET / MOONRISE / MOONSET
# ============================================================

def rise_set(
    date,
    latitude,
    longitude,
    planet,
    event_flag,
):
    """
    Calculate local rise/set and return UTC datetime.

    Swiss Ephemeris internally uses UT for rise_trans.
    """

    # Start at local midnight expressed in UTC.
    # The caller supplies timezone-independent calendar date.
    start = datetime(
        date.year,
        date.month,
        date.day,
        0,
        0,
        0,
        tzinfo=timezone.utc,
    )

    jd = jd_from_datetime(start)

    geopos = (
        longitude,
        latitude,
        0.0,
    )

    result = swe.rise_trans(
        jd,
        planet,
        event_flag,
        geopos,
        0.0,
        0.0,
        flags=swe.FLG_SWIEPH,
    )

    if not result:
        return None

    # Swiss Ephemeris versions return (status, (jd_event,))
    try:
        event_jd = result[1][0]
    except (IndexError, TypeError):
        return None

    return datetime_from_jd(event_jd)


# ============================================================
# PANCHANG ANGAS
# ============================================================

def get_tithi(sun, moon):
    """
    Tithi = 12 degree separation of Moon and Sun.
    """

    diff = normalize(moon - sun)

    number = int(diff / 12.0) + 1

    if number <= 15:
        name = TITHIS[number - 1]
        paksha = "Shukla"
    else:
        paksha = "Krishna"

        if number == 30:
            name = "Amavasya"
        else:
            name = TITHIS[number - 16]

    return {
        "number": number,
        "name": name,
        "paksha": paksha,
    }


def get_nakshatra(moon):
    """
    27 Nakshatras, each 13°20'.
    """

    size = 360.0 / 27.0

    index = min(
        26,
        int(moon / size),
    )

    position = (
        moon
        - index * size
    )

    pada = min(
        4,
        int(position / (size / 4.0)) + 1,
    )

    return {
        "number": index + 1,
        "name": NAKSHATRAS[index],
        "pada": pada,
    }


def get_yoga(sun, moon):
    """
    Yoga = sidereal Sun + sidereal Moon.
    """

    value = normalize(sun + moon)

    size = 360.0 / 27.0

    index = min(
        26,
        int(value / size),
    )

    return {
        "number": index + 1,
        "name": YOGAS[index],
    }


def get_karana(sun, moon):
    """
    Karana is half a tithi.
    """

    diff = normalize(moon - sun)

    half = int(diff / 6.0) + 1

    if half == 1:
        name = "Kimstughna"

    elif half == 58:
        name = "Shakuni"

    elif half == 59:
        name = "Chatushpada"

    elif half == 60:
        name = "Naga"

    else:
        name = KARANAS_MOVABLE[
            (half - 2) % 7
        ]

    return {
        "number": half,
        "name": name,
    }


# ============================================================
# RASHI
# ============================================================

def get_rashi(longitude):
    index = min(
        11,
        int(normalize(longitude) / 30.0),
    )

    return {
        "number": index + 1,
        "name": SIGNS[index],
        "longitude": normalize(longitude),
    }


# ============================================================
# TRANSITION SEARCH
# ============================================================

def find_transition(
    start,
    end,
    function,
    old_value,
):
    """
    Find the exact moment a Panchang anga changes.

    The search first brackets the transition using a small
    interval and then binary-searches the transition.
    """

    step = timedelta(
        minutes=2
    )

    current = start
    previous = old_value

    while current < end:

        nxt = min(
            current + step,
            end,
        )

        value = function(
            jd_from_datetime(nxt)
        )

        if value != previous:

            low = current
            high = nxt

            for _ in range(40):

                middle = (
                    low
                    + (high - low) / 2
                )

                middle_value = function(
                    jd_from_datetime(middle)
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
# TIME FORMATTING
# ============================================================

def local_time(dt, timezone_name):
    if not dt:
        return None

    return (
        dt.astimezone(
            ZoneInfo(timezone_name)
        )
        .strftime("%I:%M:%S %p")
        .lstrip("0")
    )


def local_date_time(dt, timezone_name):
    if not dt:
        return None

    return (
        dt.astimezone(
            ZoneInfo(timezone_name)
        )
        .strftime("%Y-%m-%d %I:%M:%S %p")
        .lstrip("0")
    )


def iso_local(dt, timezone_name):
    if not dt:
        return None

    return (
        dt.astimezone(
            ZoneInfo(timezone_name)
        )
        .isoformat()
    )


def range_text(
    start,
    end,
    timezone_name,
):
    if not start or not end:
        return None

    return (
        local_time(start, timezone_name)
        + " – "
        + local_time(end, timezone_name)
    )


def duration_text(delta):
    if not delta:
        return None

    total = max(
        0,
        int(delta.total_seconds()),
    )

    hours = total // 3600

    minutes = (
        total % 3600
    ) // 60

    seconds = (
        total % 60
    )

    return (
        f"{hours}h "
        f"{minutes}m "
        f"{seconds}s"
    )


# ============================================================
# MUHURTA
# ============================================================

def day_segment(
    sunrise,
    sunset,
    index,
):
    duration = (
        sunset - sunrise
    ) / 8

    return (
        sunrise + duration * index,
        sunrise + duration * (index + 1),
    )


def get_muhurta(
    sunrise,
    sunset,
    weekday,
):
    rahu = day_segment(
        sunrise,
        sunset,
        RAHU[weekday] - 1,
    )

    yamaganda = day_segment(
        sunrise,
        sunset,
        YAMAGANDA[weekday] - 1,
    )

    gulika = day_segment(
        sunrise,
        sunset,
        GULIKA[weekday] - 1,
    )

    day_length = (
        sunset - sunrise
    )

    midpoint = (
        sunrise
        + day_length / 2
    )

    # Traditional Abhijit approximation:
    # one fifteenth of daytime.
    abhijit_length = (
        day_length / 15
    )

    abhijit = (
        midpoint - abhijit_length / 2,
        midpoint + abhijit_length / 2,
    )

    # Brahma Muhurta = 1h36m before sunrise.
    brahma = (
        sunrise - timedelta(minutes=96),
        sunrise,
    )

    return {
        "rahuKaal": rahu,
        "yamaganda": yamaganda,
        "gulika": gulika,
        "abhijit": abhijit,
        "brahma": brahma,
    }


# ============================================================
# CHOGHADIYA
# ============================================================

def get_choghadiya(
    sunrise,
    sunset,
    next_sunrise,
    weekday,
):
    day = []
    night = []

    day_length = (
        sunset - sunrise
    ) / 8

    for i in range(8):

        start = (
            sunrise
            + day_length * i
        )

        end = (
            sunrise
            + day_length * (i + 1)
        )

        day.append({
            "name": CHOG_DAY[weekday][i],
            "start": start.isoformat(),
            "end": end.isoformat(),
        })

    night_length = (
        next_sunrise - sunset
    ) / 8

    for i in range(8):

        start = (
            sunset
            + night_length * i
        )

        end = (
            sunset
            + night_length * (i + 1)
        )

        night.append({
            "name": CHOG_NIGHT[weekday][i],
            "start": start.isoformat(),
            "end": end.isoformat(),
        })

    return {
        "day": day,
        "night": night,
    }


# ============================================================
# SAMVAT
# ============================================================

def get_samvat(date):
    """
    Basic Gregorian-year based labels.

    Full Vikram Samvat month/day rules should be added in the
    calendar layer because the year boundary depends on the
    regional lunar calendar convention.
    """

    return {
        "vikramSamvat": date.year + 57,
        "shakaSamvat": date.year - 78,
    }


# ============================================================
# RITU / AYANA
# ============================================================

def get_ayana(sun):
    """
    Approximate sidereal solar ayana classification.
    """

    if (
        sun >= 270
        or sun < 90
    ):
        return "Uttarayana"

    return "Dakshinayana"


def get_ritu(sun):
    names = [
        "Vasanta",
        "Grishma",
        "Varsha",
        "Sharad",
        "Hemanta",
        "Shishira",
    ]

    return names[
        min(
            5,
            int(
                normalize(sun) / 60.0
            ),
        )
    ]


# ============================================================
# FESTIVAL BASICS
# ============================================================

def get_basic_festivals(tithi):
    festivals = []

    number = tithi["number"]
    paksha = tithi["paksha"]

    if number == 11:
        festivals.append({
            "name": "Ekadashi",
            "type": "Vrat",
            "paksha": paksha,
        })

    if number == 15:
        festivals.append({
            "name": "Purnima",
            "type": "Tithi",
            "paksha": "Shukla",
        })

    if number == 30:
        festivals.append({
            "name": "Amavasya",
            "type": "Tithi",
            "paksha": "Krishna",
        })

    return festivals


# ============================================================
# COMPLETE CALCULATION
# ============================================================

def calculate_panchang(
    date,
    latitude,
    longitude,
    timezone_name,
):
    tz = ZoneInfo(
        timezone_name
    )

    local_midnight = datetime(
        date.year,
        date.month,
        date.day,
        0,
        0,
        0,
        tzinfo=tz,
    )

    next_local_midnight = (
        local_midnight
        + timedelta(days=1)
    )

    calculation_start = (
        local_midnight
        - timedelta(hours=3)
    ).astimezone(timezone.utc)

    calculation_end = (
        next_local_midnight
        + timedelta(hours=3)
    ).astimezone(timezone.utc)

    # --------------------------------------------------------
    # SUN / MOON EVENTS
    # --------------------------------------------------------

    sunrise = rise_set(
        date,
        latitude,
        longitude,
        swe.SUN,
        swe.CALC_RISE,
    )

    sunset = rise_set(
        date,
        latitude,
        longitude,
        swe.SUN,
        swe.CALC_SET,
    )

    moonrise = rise_set(
        date,
        latitude,
        longitude,
        swe.MOON,
        swe.CALC_RISE,
    )

    moonset = rise_set(
        date,
        latitude,
        longitude,
        swe.MOON,
        swe.CALC_SET,
    )

    next_date = (
        date + timedelta(days=1)
    )

    next_sunrise = rise_set(
        next_date,
        latitude,
        longitude,
        swe.SUN,
        swe.CALC_RISE,
    )

    if not sunrise or not sunset:
        raise RuntimeError(
            "Unable to calculate sunrise/sunset "
            "for the supplied coordinates."
        )

    # --------------------------------------------------------
    # PANCHANG AT SUNRISE
    # --------------------------------------------------------

    sunrise_jd = jd_from_datetime(
        sunrise
    )

    sun, moon = sun_moon(
        sunrise_jd
    )

    tithi = get_tithi(
        sun,
        moon
    )

    nakshatra = get_nakshatra(
        moon
    )

    yoga = get_yoga(
        sun,
        moon
    )

    karana = get_karana(
        sun,
        moon
    )

    moon_rashi = get_rashi(
        moon
    )

    sun_rashi = get_rashi(
        sun
    )

    # --------------------------------------------------------
    # PANCHANG TRANSITIONS
    # --------------------------------------------------------

    search_start = sunrise
    search_end = (
        next_local_midnight
        .astimezone(timezone.utc)
        + timedelta(minutes=1)
    )

    tithi_end = find_transition(
        search_start,
        search_end,
        lambda jd: get_tithi(
            *sun_moon(jd)
        )["number"],
        tithi["number"],
    )

    nakshatra_end = find_transition(
        search_start,
        search_end,
        lambda jd: get_nakshatra(
            sun_moon(jd)[1]
        )["number"],
        nakshatra["number"],
    )

    yoga_end = find_transition(
        search_start,
        search_end,
        lambda jd: get_yoga(
            *sun_moon(jd)
        )["number"],
        yoga["number"],
    )

    karana_end = find_transition(
        search_start,
        search_end,
        lambda jd: get_karana(
            *sun_moon(jd)
        )["number"],
        karana["number"],
    )

    # --------------------------------------------------------
    # WEEKDAY
    # --------------------------------------------------------

    weekday = date.weekday()

    # Python:
    # Monday = 0
    #
    # Our constants:
    # Sunday = 0
    #
    sunday_based_weekday = (
        (weekday + 1) % 7
    )

    # --------------------------------------------------------
    # MUHURTA
    # --------------------------------------------------------

    muhurta = get_muhurta(
        sunrise,
        sunset,
        sunday_based_weekday,
    )

    # --------------------------------------------------------
    # CHOGHADIYA
    # --------------------------------------------------------

    if next_sunrise:

        choghadiya = get_choghadiya(
            sunrise,
            sunset,
            next_sunrise,
            sunday_based_weekday,
        )

    else:

        choghadiya = {
            "day": [],
            "night": [],
        }

    # --------------------------------------------------------
    # AYANA / RITU
    # --------------------------------------------------------

    ayana = get_ayana(
        sun
    )

    ritu = get_ritu(
        sun
    )

    # --------------------------------------------------------
    # SAMVAT
    # --------------------------------------------------------

    samvat = get_samvat(
        date
    )

    # --------------------------------------------------------
    # FESTIVALS
    # --------------------------------------------------------

    festivals = get_basic_festivals(
        tithi
    )

    # --------------------------------------------------------
    # DAY / NIGHT DURATION
    # --------------------------------------------------------

    day_duration = (
        sunset - sunrise
    )

    night_duration = None

    if next_sunrise:
        night_duration = (
            next_sunrise - sunset
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "success": True,

        "engine": {
            "name": "Mauksh Panchang Engine",
            "version": "3.0",
            "ephemeris": "Swiss Ephemeris",
            "ayanamsa": "Lahiri",
        },

        "date": date.isoformat(),

        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone_name,
        },

        "vara": {
            "number": sunday_based_weekday + 1,
            "name": WEEKDAYS[
                sunday_based_weekday
            ],
        },

        "sun": {
            "rise": local_time(
                sunrise,
                timezone_name,
            ),
            "riseISO": iso_local(
                sunrise,
                timezone_name,
            ),
            "set": local_time(
                sunset,
                timezone_name,
            ),
            "setISO": iso_local(
                sunset,
                timezone_name,
            ),
            "rashi": sun_rashi,
        },

        "moon": {
            "rise": local_time(
                moonrise,
                timezone_name,
            ),
            "riseISO": iso_local(
                moonrise,
                timezone_name,
            ),
            "set": local_time(
                moonset,
                timezone_name,
            ),
            "setISO": iso_local(
                moonset,
                timezone_name,
            ),
            "rashi": moon_rashi,
            "nakshatra": nakshatra,
        },

        "tithi": {
            "number": tithi["number"],
            "name": tithi["name"],
            "paksha": tithi["paksha"],
            "ends": local_time(
                tithi_end,
                timezone_name,
            ),
            "endsISO": iso_local(
                tithi_end,
                timezone_name,
            ),
        },

        "nakshatra": {
            "number": nakshatra["number"],
            "name": nakshatra["name"],
            "pada": nakshatra["pada"],
            "ends": local_time(
                nakshatra_end,
                timezone_name,
            ),
            "endsISO": iso_local(
                nakshatra_end,
                timezone_name,
            ),
        },

        "yoga": {
            "number": yoga["number"],
            "name": yoga["name"],
            "ends": local_time(
                yoga_end,
                timezone_name,
            ),
            "endsISO": iso_local(
                yoga_end,
                timezone_name,
            ),
        },

        "karana": {
            "number": karana["number"],
            "name": karana["name"],
            "ends": local_time(
                karana_end,
                timezone_name,
            ),
            "endsISO": iso_local(
                karana_end,
                timezone_name,
            ),
        },

        "rashi": {
            "sun": sun_rashi,
            "moon": moon_rashi,
        },

        "paksha": tithi["paksha"],

        "ayana": ayana,

        "ritu": ritu,

        "dayDuration": duration_text(
            day_duration
        ),

        "nightDuration": duration_text(
            night_duration
        ),

        "timings": {
            "rahuKaal": range_text(
                *muhurta["rahuKaal"],
                timezone_name,
            ),
            "yamaganda": range_text(
                *muhurta["yamaganda"],
                timezone_name,
            ),
            "gulika": range_text(
                *muhurta["gulika"],
                timezone_name,
            ),
            "abhijit": range_text(
                *muhurta["abhijit"],
                timezone_name,
            ),
            "brahma": range_text(
                *muhurta["brahma"],
                timezone_name,
            ),
        },

        "timingsISO": {
            "rahuKaal": [
                iso_local(
                    muhurta["rahuKaal"][0],
                    timezone_name,
                ),
                iso_local(
                    muhurta["rahuKaal"][1],
                    timezone_name,
                ),
            ],

            "yamaganda": [
                iso_local(
                    muhurta["yamaganda"][0],
                    timezone_name,
                ),
                iso_local(
                    muhurta["yamaganda"][1],
                    timezone_name,
                ),
            ],

            "gulika": [
                iso_local(
                    muhurta["gulika"][0],
                    timezone_name,
                ),
                iso_local(
                    muhurta["gulika"][1],
                    timezone_name,
                ),
            ],

            "abhijit": [
                iso_local(
                    muhurta["abhijit"][0],
                    timezone_name,
                ),
                iso_local(
                    muhurta["abhijit"][1],
                    timezone_name,
                ),
            ],

            "brahma": [
                iso_local(
                    muhurta["brahma"][0],
                    timezone_name,
                ),
                iso_local(
                    muhurta["brahma"][1],
                    timezone_name,
                ),
            ],
        },

        "choghadiya": choghadiya,

        "festivals": festivals,

        "samvat": samvat,

        "vikramSamvat": samvat[
            "vikramSamvat"
        ],

        "shakaSamvat": samvat[
            "shakaSamvat"
        ],
    }


# ============================================================
# API ENDPOINT
# ============================================================

@panchang_api.route(
    "/api/panchang",
    methods=["GET"],
)
def panchang():

    try:

        date_string = request.args.get(
            "date"
        )

        latitude = request.args.get(
            "latitude",
            type=float,
        )

        longitude = request.args.get(
            "longitude",
            type=float,
        )

        timezone_name = request.args.get(
            "timezone",
            "Asia/Kolkata",
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not date_string:

            return jsonify({
                "success": False,
                "error": "date is required",
            }), 400

        if latitude is None:

            return jsonify({
                "success": False,
                "error": "latitude is required",
            }), 400

        if longitude is None:

            return jsonify({
                "success": False,
                "error": "longitude is required",
            }), 400

        if not -90 <= latitude <= 90:

            return jsonify({
                "success": False,
                "error": "Invalid latitude",
            }), 400

        if not -180 <= longitude <= 180:

            return jsonify({
                "success": False,
                "error": "Invalid longitude",
            }), 400

        try:

            ZoneInfo(
                timezone_name
            )

        except Exception:

            return jsonify({
                "success": False,
                "error": "Invalid timezone",
            }), 400

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        try:

            date = datetime.strptime(
                date_string,
                "%Y-%m-%d",
            ).date()

        except ValueError:

            return jsonify({
                "success": False,
                "error":
                    "Invalid date. "
                    "Use YYYY-MM-DD",
            }), 400

        # ----------------------------------------------------
        # CALCULATE
        # ----------------------------------------------------

        result = calculate_panchang(
            date,
            latitude,
            longitude,
            timezone_name,
        )

        return jsonify(
            result
        )

    except Exception as exc:

        print(
            "Panchang API error:",
            repr(exc),
        )

        return jsonify({
            "success": False,
            "error": str(exc),
        }), 500