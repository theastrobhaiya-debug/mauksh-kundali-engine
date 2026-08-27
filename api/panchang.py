from flask import Blueprint, request, jsonify
import swisseph as swe
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

panchang_api = Blueprint("panchang_api", __name__)

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
    "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
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
    "Bava", "Balava", "Kaulava", "Taitila",
    "Garaja", "Vanija", "Vishti"
]

VARAS = [
    "Sunday", "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday"
]


def norm(x):
    return x % 360.0


def jd_from_utc(dt):
    return swe.julday(
        dt.year,
        dt.month,
        dt.day,
        dt.hour + dt.minute / 60 +
        dt.second / 3600
    )


def sidereal_longitude(jd, planet):
    result, _ = swe.calc_ut(
        jd,
        planet,
        swe.FLG_SWIEPH |
        swe.FLG_SIDEREAL
    )
    return norm(result[0])


def get_sun_moon(jd):
    return (
        sidereal_longitude(jd, swe.SUN),
        sidereal_longitude(jd, swe.MOON)
    )


def tithi_info(sun, moon):
    diff = norm(moon - sun)
    index = int(diff / 12)
    fraction = (diff % 12) / 12

    paksha = "Shukla Paksha" if index < 15 else "Krishna Paksha"

    names = [
        "Pratipada", "Dvitiya", "Tritiya", "Chaturthi",
        "Panchami", "Shashthi", "Saptami", "Ashtami",
        "Navami", "Dashami", "Ekadashi", "Dwadashi",
        "Trayodashi", "Chaturdashi", "Purnima"
    ]

    if index == 30 - 1:
        name = "Amavasya"
    else:
        name = names[index % 15]

    return name, paksha, fraction


def nakshatra_info(moon):
    size = 360 / 27
    index = int(moon / size)
    position = (moon % size) / size

    pada = int(position * 4) + 1

    return (
        NAKSHATRAS[index],
        pada,
        position
    )


def yoga_info(sun, moon):
    value = norm(sun + moon)
    size = 360 / 27

    index = int(value / size)
    fraction = (value % size) / size

    return YOGAS[index], fraction


def karana_info(sun, moon):
    diff = norm(moon - sun)
    half_index = int(diff / 6)

    if half_index == 0:
        return "Kimstughna"

    if half_index >= 57:
        return "Shakuni" if half_index == 57 else (
            "Chatushpada" if half_index == 58 else "Naga"
        )

    return KARANAS[(half_index - 1) % 7]


def find_boundary(
    start_utc,
    end_utc,
    calculation,
    target
):
    step = timedelta(minutes=10)

    current = start_utc
    previous = calculation(current)

    while current < end_utc:
        nxt = min(current + step, end_utc)
        value = calculation(nxt)

        if value != previous:
            low = current
            high = nxt

            for _ in range(25):
                mid = low + (high - low) / 2

                if calculation(mid) == previous:
                    low = mid
                else:
                    high = mid

            return high

        previous = value
        current = nxt

    return None


def format_local(dt, tz):
    if not dt:
        return None

    return dt.astimezone(tz).strftime(
        "%I:%M %p"
    ).lstrip("0")


def sunrise_sunset(date, latitude, longitude, tz):
    midnight = datetime(
        date.year,
        date.month,
        date.day,
        tzinfo=timezone.utc
    )

    jd = jd_from_utc(midnight)

    rise = swe.rise_trans(
        jd,
        swe.SUN,
        swe.CALC_RISE,
        (longitude, latitude, 0)
    )

    setting = swe.rise_trans(
        jd,
        swe.SUN,
        swe.CALC_SET,
        (longitude, latitude, 0)
    )

    sunrise_jd = rise[1][0]
    sunset_jd = setting[1][0]

    return (
        swe.jdut1_to_utc(
            sunrise_jd,
            swe.GREG_CAL
        ),
        swe.jdut1_to_utc(
            sunset_jd,
            swe.GREG_CAL
        )
    )


def calculate_panchang(
    date,
    latitude,
    longitude,
    timezone_name
):
    tz = ZoneInfo(timezone_name)

    local_midnight = datetime(
        date.year,
        date.month,
        date.day,
        tzinfo=tz
    )

    start = local_midnight.astimezone(timezone.utc)
    end = (
        local_midnight +
        timedelta(days=1)
    ).astimezone(timezone.utc)

    sunrise, sunset = sunrise_sunset(
        date,
        latitude,
        longitude,
        tz
    )

    sunrise_dt = datetime(
        sunrise[0],
        sunrise[1],
        sunrise[2],
        sunrise[3],
        sunrise[4],
        sunrise[5],
        tzinfo=timezone.utc
    )

    sunset_dt = datetime(
        sunset[0],
        sunset[1],
        sunset[2],
        sunset[3],
        sunset[4],
        sunset[5],
        tzinfo=timezone.utc
    )

    jd = jd_from_utc(sunrise_dt)

    sun, moon = get_sun_moon(jd)

    tithi, paksha, _ = tithi_info(
        sun,
        moon
    )

    nakshatra, pada, _ = nakshatra_info(
        moon
    )

    yoga, _ = yoga_info(
        sun,
        moon
    )

    karana = karana_info(
        sun,
        moon
    )

    weekday = date.weekday()

    vara = VARAS[
        (weekday + 1) % 7
    ]

    moon_rashi = SIGNS[
        int(moon / 30)
    ]

    sun_rashi = SIGNS[
        int(sun / 30)
    ]

    tithi_end = find_boundary(
        sunrise_dt,
        end,
        lambda dt: tithi_info(
            *get_sun_moon(
                jd_from_utc(dt)
            )
        )[0],
        tithi
    )

    nakshatra_end = find_boundary(
        sunrise_dt,
        end,
        lambda dt: nakshatra_info(
            get_sun_moon(
                jd_from_utc(dt)
            )[1]
        )[0],
        nakshatra
    )

    yoga_end = find_boundary(
        sunrise_dt,
        end,
        lambda dt: yoga_info(
            *get_sun_moon(
                jd_from_utc(dt)
            )
        )[0],
        yoga
    )

    day_duration = sunset_dt - sunrise_dt

    return {
        "success": True,

        "date": date.isoformat(),

        "sunrise": format_local(
            sunrise_dt,
            tz
        ),

        "sunset": format_local(
            sunset_dt,
            tz
        ),

        "moonrise": None,
        "moonset": None,

        "tithi": {
            "name": tithi,
            "end": format_local(
                tithi_end,
                tz
            )
        },

        "vara": {
            "name": vara
        },

        "nakshatra": {
            "name": nakshatra,
            "pada": pada,
            "end": format_local(
                nakshatra_end,
                tz
            )
        },

        "yoga": {
            "name": yoga,
            "end": format_local(
                yoga_end,
                tz
            )
        },

        "karana": {
            "name": karana
        },

        "moonRashi": moon_rashi,
        "sunRashi": sun_rashi,
        "moonNakshatra": nakshatra,

        "paksha": paksha,

        "ayana": (
            "Uttarayana"
            if sun_rashi in [
                "Capricorn",
                "Aquarius",
                "Pisces",
                "Aries",
                "Taurus",
                "Gemini"
            ]
            else "Dakshinayana"
        ),

        "ritu": None,

        "dayDuration": str(
            day_duration
        ).split(".")[0],

        "nightDuration": None,

        "vikramSamvat": None,
        "shakaSamvat": None,

        "sunDay": vara,

        "timings": {
            "rahuKaal": None,
            "yamaganda": None,
            "gulika": None,
            "abhijit": None,
            "brahma": None,
            "durMuhurat": None,
            "varjyam": None,
            "amritKaal": None
        },

        "choghadiya": {
            "day": [],
            "night": []
        },

        "festivals": []
    }


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
                "error": "date is required"
            }), 400

        if latitude is None or longitude is None:
            return jsonify({
                "success": False,
                "error":
                    "latitude and longitude are required"
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

        return jsonify(result)

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500
