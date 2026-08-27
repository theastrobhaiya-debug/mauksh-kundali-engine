from flask import Blueprint, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

panchang_api = Blueprint("panchang_api", __name__)

# ============================================================
# MAUKSH PANCHANG ENGINE
# ============================================================

swe.set_sid_mode(swe.SIDM_LAHIRI)

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

YOGAS = [
    "Vishkumbha", "Priti", "Ayushman", "Saubhagya",
    "Shobhana", "Atiganda", "Sukarma", "Dhriti",
    "Shula", "Ganda", "Vriddhi", "Dhruva",
    "Vyaghata", "Harshana", "Vajra", "Siddhi",
    "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla",
    "Brahma", "Indra", "Vaidhriti"
]

TITHIS = [
    "Pratipada", "Dvitiya", "Tritiya", "Chaturthi",
    "Panchami", "Shashthi", "Saptami", "Ashtami",
    "Navami", "Dashami", "Ekadashi", "Dwadashi",
    "Trayodashi", "Chaturdashi", "Purnima"
]

KARANAS = [
    "Bava", "Balava", "Kaulava",
    "Taitila", "Garaja", "Vanija", "Vishti"
]

WEEKDAYS = [
    "Sunday", "Monday", "Tuesday",
    "Wednesday", "Thursday", "Friday", "Saturday"
]

RAHU = [8, 2, 7, 5, 6, 4, 3]
YAMAGANDA = [5, 4, 3, 2, 1, 7, 6]
GULIKA = [7, 6, 5, 4, 3, 2, 1]

CHOG_DAY = {
    0: ["Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg"],
    1: ["Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit"],
    2: ["Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog"],
    3: ["Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh"],
    4: ["Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal", "Shubh"],
    5: ["Chal", "Labh", "Amrit", "Kaal", "Shubh", "Rog", "Udveg", "Chal"],
    6: ["Kaal", "Shubh", "Rog", "Udveg", "Chal", "Labh", "Amrit", "Kaal"]
}

CHOG_NIGHT = {
    0: ["Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh"],
    1: ["Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Chal"],
    2: ["Kaal", "Labh", "Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal"],
    3: ["Rog", "Udveg", "Shubh", "Amrit", "Chal", "Kaal", "Labh", "Rog"],
    4: ["Labh", "Kaal", "Chal", "Udveg", "Shubh", "Rog", "Amrit", "Labh"],
    5: ["Udveg", "Shubh", "Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg"],
    6: ["Amrit", "Chal", "Rog", "Kaal", "Labh", "Udveg", "Shubh", "Amrit"]
}


# ============================================================
# ASTRONOMY
# ============================================================

def jd_from_datetime(dt):
    return swe.julday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour
        + dt.minute / 60
        + dt.second / 3600
        + dt.microsecond / 3600000000
    )


def normalize(x):
    return x % 360.0


def sidereal_longitude(jd, planet):
    result, _ = swe.calc_ut(
        jd,
        planet,
        swe.FLG_SWIEPH |
        swe.FLG_SIDEREAL
    )
    return normalize(result[0])


def sun_moon(jd):
    return (
        sidereal_longitude(jd, swe.SUN),
        sidereal_longitude(jd, swe.MOON)
    )


# ============================================================
# RISE / SET
# ============================================================

def rise_set(
    date,
    latitude,
    longitude,
    planet,
    event
):
    """
    Correct pyswisseph rise_trans call.

    event:
      swe.CALC_RISE
      swe.CALC_SET
    """

    midnight = datetime(
        date.year,
        date.month,
        date.day,
        tzinfo=timezone.utc
    )

    jd = jd_from_datetime(midnight)

    geopos = (
        float(longitude),
        float(latitude),
        0.0
    )

    try:

        result = swe.rise_trans(
            jd,
            planet,
            "",
            swe.BIT_DISC_CENTER,
            event,
            geopos,
            0.0,
            0.0
        )

        return jd_to_datetime(
            result[1][0]
        )

    except Exception as exc:

        print(
            "Swiss Ephemeris rise/set error:",
            exc
        )

        return None


def jd_to_datetime(jd):

    y, m, d, hour = swe.jdut1_to_utc(
        jd,
        swe.GREG_CAL
    )

    h = int(hour)

    minute_float = (
        hour - h
    ) * 60

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


# ============================================================
# PANCHANG ANGAS
# ============================================================

def get_tithi(sun, moon):

    diff = normalize(
        moon - sun
    )

    number = int(
        diff / 12
    ) + 1

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
        "paksha": paksha
    }


def get_nakshatra(moon):

    size = 360 / 27

    index = min(
        26,
        int(moon / size)
    )

    position = (
        moon -
        index * size
    )

    pada = min(
        4,
        int(
            position /
            (size / 4)
        ) + 1
    )

    return {
        "number": index + 1,
        "name": NAKSHATRAS[index],
        "pada": pada
    }


def get_yoga(sun, moon):

    value = normalize(
        sun + moon
    )

    size = 360 / 27

    index = min(
        26,
        int(value / size)
    )

    return {
        "number": index + 1,
        "name": YOGAS[index]
    }


def get_karana(sun, moon):

    diff = normalize(
        moon - sun
    )

    half = int(
        diff / 6
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
        name = KARANAS[
            (half - 2) % 7
        ]

    return {
        "number": half,
        "name": name
    }


# ============================================================
# FORMATTING
# ============================================================

def local_time(dt, timezone_name):

    if not dt:
        return None

    return dt.astimezone(
        ZoneInfo(timezone_name)
    ).strftime(
        "%I:%M %p"
    ).lstrip("0")


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


def duration_text(delta):

    if not delta:
        return None

    total = int(
        delta.total_seconds()
    )

    hours = total // 3600

    minutes = (
        total % 3600
    ) // 60

    return (
        f"{hours}h {minutes}m"
    )


# ============================================================
# TRANSITION SEARCH
# ============================================================

def find_transition(
    start,
    end,
    function,
    old_value
):

    step = timedelta(
        minutes=5
    )

    current = start

    previous = old_value

    while current < end:

        nxt = min(
            current + step,
            end
        )

        jd = jd_from_datetime(
            nxt
        )

        value = function(
            jd
        )

        if value != previous:

            low = current
            high = nxt

            for _ in range(30):

                middle = (
                    low +
                    (high - low) / 2
                )

                middle_value = function(
                    jd_from_datetime(
                        middle
                    )
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
# MUHURTA
# ============================================================

def day_segment(
    sunrise,
    sunset,
    index
):

    duration = (
        sunset - sunrise
    ) / 8

    return (
        sunrise +
        duration * index,
        sunrise +
        duration * (index + 1)
    )


def get_muhurta(
    sunrise,
    sunset,
    weekday
):

    rahu = day_segment(
        sunrise,
        sunset,
        RAHU[weekday] - 1
    )

    yamaganda = day_segment(
        sunrise,
        sunset,
        YAMAGANDA[weekday] - 1
    )

    gulika = day_segment(
        sunrise,
        sunset,
        GULIKA[weekday] - 1
    )

    day_length = (
        sunset - sunrise
    )

    midpoint = (
        sunrise +
        day_length / 2
    )

    abhijit_length = (
        day_length / 15
    )

    abhijit = (
        midpoint -
        abhijit_length / 2,
        midpoint +
        abhijit_length / 2
    )

    brahma = (
        sunrise -
        timedelta(minutes=96),
        sunrise
    )

    return {
        "rahuKaal": rahu,
        "yamaganda": yamaganda,
        "gulika": gulika,
        "abhijit": abhijit,
        "brahma": brahma
    }


# ============================================================
# CHOGHADIYA
# ============================================================

def get_choghadiya(
    sunrise,
    sunset,
    next_sunrise,
    weekday
):

    day = []

    night = []

    day_length = (
        sunset - sunrise
    ) / 8

    for i in range(8):

        start = (
            sunrise +
            day_length * i
        )

        end = (
            sunrise +
            day_length * (i + 1)
        )

        day.append({
            "name":
                CHOG_DAY[weekday][i],
            "start":
                start.isoformat(),
            "end":
                end.isoformat()
        })

    night_length = (
        next_sunrise - sunset
    ) / 8

    for i in range(8):

        start = (
            sunset +
            night_length * i
        )

        end = (
            sunset +
            night_length * (i + 1)
        )

        night.append({
            "name":
                CHOG_NIGHT[weekday][i],
            "start":
                start.isoformat(),
            "end":
                end.isoformat()
        })

    return {
        "day": day,
        "night": night
    }


# ============================================================
# MAIN
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

    local_midnight = datetime(
        date.year,
        date.month,
        date.day,
        tzinfo=tz
    )

    next_local_midnight = (
        local_midnight +
        timedelta(days=1)
    )

    day_end_utc = (
        next_local_midnight
        .astimezone(timezone.utc)
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

    next_sunrise = rise_set(
        date + timedelta(days=1),
        latitude,
        longitude,
        swe.SUN,
        swe.CALC_RISE
    )

    sun, moon = sun_moon(
        jd_from_datetime(
            sunrise
        )
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

    weekday = (
        date.weekday() + 1
    ) % 7

    # ----------------------------
    # TRANSITIONS
    # ----------------------------

    tithi_end = find_transition(
        sunrise,
        day_end_utc,
        lambda jd:
            get_tithi(
                *sun_moon(jd)
            )["number"],
        tithi["number"]
    )

    nakshatra_end = find_transition(
        sunrise,
        day_end_utc,
        lambda jd:
            get_nakshatra(
                sun_moon(jd)[1]
            )["number"],
        nakshatra["number"]
    )

    yoga_end = find_transition(
        sunrise,
        day_end_utc,
        lambda jd:
            get_yoga(
                *sun_moon(jd)
            )["number"],
        yoga["number"]
    )

    # ----------------------------
    # RASHI
    # ----------------------------

    moon_rashi = SIGNS[
        int(moon / 30)
    ]

    sun_rashi = SIGNS[
        int(sun / 30)
    ]

    # ----------------------------
    # AYANA
    # ----------------------------

    ayana = (
        "Uttarayana"
        if sun >= 270 or sun < 90
        else "Dakshinayana"
    )

    # ----------------------------
    # RITU
    # ----------------------------

    ritu_names = [
        "Vasanta",
        "Grishma",
        "Varsha",
        "Sharad",
        "Hemanta",
        "Shishira"
    ]

    ritu = ritu_names[
        int(sun / 60)
    ]

    # ----------------------------
    # MUHURTA
    # ----------------------------

    muhurta = get_muhurta(
        sunrise,
        sunset,
        weekday
    )

    # ----------------------------
    # CHOGHADIYA
    # ----------------------------

    if next_sunrise:

        choghadiya = get_choghadiya(
            sunrise,
            sunset,
            next_sunrise,
            weekday
        )

    else:

        choghadiya = {
            "day": [],
            "night": []
        }

    # ----------------------------
    # FESTIVALS / VRAT
    # ----------------------------

    festivals = []

    if tithi["number"] in (11, 26):

        festivals.append({
            "name": "Ekadashi",
            "type": "Vrat",
            "paksha":
                tithi["paksha"]
        })

    if tithi["number"] == 15:

        festivals.append({
            "name": "Purnima",
            "type": "Tithi",
            "paksha": "Shukla"
        })

    if tithi["number"] == 30:

        festivals.append({
            "name": "Amavasya",
            "type": "Tithi",
            "paksha": "Krishna"
        })

    if tithi["number"] in (13, 28):

        festivals.append({
            "name": "Pradosh Vrat",
            "type": "Vrat",
            "paksha":
                tithi["paksha"]
        })

    if (
        tithi["number"] == 19
        and tithi["paksha"] == "Krishna"
    ):

        festivals.append({
            "name": "Sankashti Chaturthi",
            "type": "Vrat",
            "paksha": "Krishna"
        })

    if (
        tithi["number"] == 29
        and tithi["paksha"] == "Krishna"
    ):

        festivals.append({
            "name": "Masik Shivaratri",
            "type": "Vrat",
            "paksha": "Krishna"
        })

    # ----------------------------
    # RESPONSE
    # ----------------------------

    return {

        "success": True,

        "engine": "Mauksh Panchang Engine",

        "version": "2.1",

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
            moon_rashi,

        "sunRashi":
            sun_rashi,

        "moonNakshatra":
            nakshatra["name"],

        "paksha":
            tithi["paksha"],

        "ayana":
            ayana,

        "ritu":
            ritu,

        "dayDuration":
            duration_text(
                sunset - sunrise
            ),

        "nightDuration":
            duration_text(
                next_sunrise - sunset
            )
            if next_sunrise else None,

        "timings": {

            "rahuKaal":
                range_text(
                    *muhurta["rahuKaal"],
                    timezone_name
                ),

            "yamaganda":
                range_text(
                    *muhurta["yamaganda"],
                    timezone_name
                ),

            "gulika":
                range_text(
                    *muhurta["gulika"],
                    timezone_name
                ),

            "abhijit":
                range_text(
                    *muhurta["abhijit"],
                    timezone_name
                ),

            "brahma":
                range_text(
                    *muhurta["brahma"],
                    timezone_name
                )
        },

        "choghadiya":
            choghadiya,

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
# API
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

        print(
            "Panchang API error:",
            exc
        )

        return jsonify({
            "success": False,
            "error":
                str(exc)
        }), 500