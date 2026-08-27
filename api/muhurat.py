# ============================================================
# MAUKSH MUHURAT ENGINE
# Purpose-specific Vedic Muhurta calculator
# Uses the existing Mauksh Panchang Engine
# Swiss Ephemeris + Lahiri Ayanamsa
# ============================================================

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, jsonify, request

from api.panchang import calculate_panchang


muhurat_api = Blueprint("muhurat_api", __name__)


# ============================================================
# PURPOSE RULES
# ============================================================

PURPOSES = {

    "marriage": {
        "name": "Marriage",

        "nakshatra": {
            "Rohini",
            "Mrigashira",
            "Magha",
            "Uttara Phalguni",
            "Hasta",
            "Swati",
            "Anuradha",
            "Mula",
            "Shravana",
            "Dhanishtha",
            "Shatabhisha",
            "Uttara Bhadrapada",
            "Revati",
        },

        "tithi": {
            "Dwitiya",
            "Tritiya",
            "Panchami",
            "Saptami",
            "Dashami",
            "Ekadashi",
            "Trayodashi",
        },

        "weekday": {
            "Monday",
            "Wednesday",
            "Thursday",
            "Friday",
        },
    },


    "property": {
        "name": "Property Purchase",

        "nakshatra": {
            "Rohini",
            "Mrigashira",
            "Punarvasu",
            "Pushya",
            "Magha",
            "Uttara Phalguni",
            "Hasta",
            "Chitra",
            "Swati",
            "Anuradha",
            "Shravana",
            "Dhanishtha",
            "Shatabhisha",
            "Uttara Bhadrapada",
            "Revati",
        },

        "tithi": {
            "Dwitiya",
            "Tritiya",
            "Panchami",
            "Saptami",
            "Dashami",
            "Ekadashi",
            "Trayodashi",
        },

        "weekday": {
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        },
    },


    "vehicle": {
        "name": "Vehicle Purchase",

        "nakshatra": {
            "Ashwini",
            "Rohini",
            "Mrigashira",
            "Punarvasu",
            "Pushya",
            "Magha",
            "Uttara Phalguni",
            "Hasta",
            "Swati",
            "Anuradha",
            "Shravana",
            "Dhanishtha",
            "Shatabhisha",
            "Uttara Bhadrapada",
            "Revati",
        },

        "tithi": {
            "Dwitiya",
            "Tritiya",
            "Panchami",
            "Saptami",
            "Dashami",
            "Ekadashi",
            "Trayodashi",
        },

        "weekday": {
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
        },
    },


    "business": {
        "name": "Business Launch",

        "nakshatra": {
            "Ashwini",
            "Rohini",
            "Mrigashira",
            "Punarvasu",
            "Pushya",
            "Hasta",
            "Chitra",
            "Swati",
            "Anuradha",
            "Shravana",
            "Dhanishtha",
            "Shatabhisha",
            "Revati",
        },

        "tithi": {
            "Dwitiya",
            "Tritiya",
            "Panchami",
            "Saptami",
            "Dashami",
            "Ekadashi",
            "Trayodashi",
        },

        "weekday": {
            "Monday",
            "Wednesday",
            "Thursday",
            "Friday",
        },
    },


    "travel": {
        "name": "Travel",

        "nakshatra": {
            "Ashwini",
            "Punarvasu",
            "Pushya",
            "Hasta",
            "Anuradha",
            "Shravana",
            "Dhanishtha",
            "Revati",
        },

        "tithi": {
            "Dwitiya",
            "Tritiya",
            "Panchami",
            "Saptami",
            "Dashami",
            "Ekadashi",
            "Trayodashi",
        },

        "weekday": {
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        },
    },


    "naming": {
        "name": "Naming Ceremony",

        "nakshatra": {
            "Ashwini",
            "Rohini",
            "Mrigashira",
            "Punarvasu",
            "Pushya",
            "Hasta",
            "Swati",
            "Anuradha",
            "Shravana",
            "Dhanishtha",
            "Shatabhisha",
            "Uttara Bhadrapada",
            "Revati",
        },

        "tithi": {
            "Dwitiya",
            "Tritiya",
            "Panchami",
            "Saptami",
            "Dashami",
            "Ekadashi",
            "Trayodashi",
        },

        "weekday": {
            "Monday",
            "Wednesday",
            "Thursday",
            "Friday",
        },
    },


    "housewarming": {
        "name": "Housewarming",

        "nakshatra": {
            "Rohini",
            "Mrigashira",
            "Punarvasu",
            "Pushya",
            "Uttara Phalguni",
            "Hasta",
            "Chitra",
            "Swati",
            "Anuradha",
            "Shravana",
            "Dhanishtha",
            "Shatabhisha",
            "Uttara Bhadrapada",
            "Revati",
        },

        "tithi": {
            "Dwitiya",
            "Tritiya",
            "Panchami",
            "Saptami",
            "Dashami",
            "Ekadashi",
            "Trayodashi",
        },

        "weekday": {
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
        },
    },


    "education": {
        "name": "Education",

        "nakshatra": {
            "Ashwini",
            "Rohini",
            "Mrigashira",
            "Punarvasu",
            "Pushya",
            "Hasta",
            "Swati",
            "Anuradha",
            "Shravana",
            "Dhanishtha",
            "Revati",
        },

        "tithi": {
            "Dwitiya",
            "Tritiya",
            "Panchami",
            "Saptami",
            "Dashami",
            "Ekadashi",
            "Trayodashi",
        },

        "weekday": {
            "Monday",
            "Wednesday",
            "Thursday",
            "Friday",
        },
    },


    "work": {
        "name": "Starting Work",

        "nakshatra": {
            "Ashwini",
            "Rohini",
            "Mrigashira",
            "Punarvasu",
            "Pushya",
            "Hasta",
            "Swati",
            "Anuradha",
            "Shravana",
            "Dhanishtha",
            "Shatabhisha",
            "Revati",
        },

        "tithi": {
            "Dwitiya",
            "Tritiya",
            "Panchami",
            "Saptami",
            "Dashami",
            "Ekadashi",
            "Trayodashi",
        },

        "weekday": {
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
        },
    },
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def parse_engine_time(value):
    """
    Convert Panchang formatted time into Python time.
    """

    return datetime.strptime(
        value,
        "%I:%M:%S %p"
    ).time()


def local_datetime(date_value, time_value, timezone_name):

    return datetime.combine(
        date_value,
        time_value,
        tzinfo=ZoneInfo(timezone_name)
    )


def parse_range(
    value,
    date_value,
    timezone_name
):

    if not value:
        return None

    if " – " not in value:
        return None

    start_text, end_text = value.split(
        " – ",
        1
    )

    start = local_datetime(
        date_value,
        parse_engine_time(start_text),
        timezone_name
    )

    end = local_datetime(
        date_value,
        parse_engine_time(end_text),
        timezone_name
    )

    return start, end


def overlaps(
    start,
    end,
    blocked_start,
    blocked_end
):

    return (
        start < blocked_end
        and end > blocked_start
    )


# ============================================================
# DAILY SCORE
# ============================================================

def calculate_day_score(
    panchang,
    purpose
):

    rules = PURPOSES[purpose]

    score = 0

    reasons = []

    nakshatra = panchang[
        "nakshatra"
    ][
        "name"
    ]

    tithi = panchang[
        "tithi"
    ][
        "name"
    ]

    weekday = panchang[
        "vara"
    ][
        "name"
    ]

    yoga = panchang[
        "yoga"
    ][
        "name"
    ]


    # --------------------------------------------------------
    # NAKSHATRA
    # --------------------------------------------------------

    if nakshatra in rules["nakshatra"]:

        score += 30

        reasons.append(
            "Favorable Nakshatra"
        )

    else:

        score -= 20


    # --------------------------------------------------------
    # TITHI
    # --------------------------------------------------------

    if tithi in rules["tithi"]:

        score += 25

        reasons.append(
            "Favorable Tithi"
        )

    else:

        score -= 15


    # --------------------------------------------------------
    # WEEKDAY
    # --------------------------------------------------------

    if weekday in rules["weekday"]:

        score += 15

        reasons.append(
            "Supportive weekday"
        )


    # --------------------------------------------------------
    # YOGA
    # --------------------------------------------------------

    unfavorable_yogas = {
        "Atiganda",
        "Shoola",
        "Ganda",
        "Vyatipata",
        "Vaidhriti",
    }

    if yoga not in unfavorable_yogas:

        score += 10

        reasons.append(
            "Supportive Yoga"
        )

    else:

        score -= 20


    return score, reasons


# ============================================================
# MUHURAT CALCULATION
# ============================================================

def calculate_muhurats(
    start_date,
    end_date,
    latitude,
    longitude,
    timezone_name,
    purpose,
    limit=30
):

    results = []

    current = start_date

    while current <= end_date:

        panchang = calculate_panchang(
            current,
            latitude,
            longitude,
            timezone_name
        )

        score, reasons = calculate_day_score(
            panchang,
            purpose
        )


        # ----------------------------------------------------
        # SUNRISE / SUNSET
        # ----------------------------------------------------

        sunrise = local_datetime(
            current,
            parse_engine_time(
                panchang["sun"]["rise"]
            ),
            timezone_name
        )

        sunset = local_datetime(
            current,
            parse_engine_time(
                panchang["sun"]["set"]
            ),
            timezone_name
        )


        # ----------------------------------------------------
        # BLOCKED PERIODS
        # ----------------------------------------------------

        blocked = []

        for key in (
            "rahuKaal",
            "yamaganda",
            "gulika"
        ):

            value = parse_range(
                panchang["timings"][key],
                current,
                timezone_name
            )

            if value:

                blocked.append(value)


        # ----------------------------------------------------
        # 15-MINUTE WINDOW SEARCH
        # ----------------------------------------------------

        candidate_slots = []

        cursor = sunrise

        while (
            cursor + timedelta(minutes=30)
            <= sunset
        ):

            slot_end = (
                cursor
                + timedelta(minutes=30)
            )

            is_blocked = False

            for blocked_start, blocked_end in blocked:

                if overlaps(
                    cursor,
                    slot_end,
                    blocked_start,
                    blocked_end
                ):

                    is_blocked = True

                    break


            if not is_blocked:

                slot_score = score

                candidate_slots.append(
                    (
                        cursor,
                        slot_end,
                        slot_score
                    )
                )


            cursor += timedelta(
                minutes=15
            )


        # ----------------------------------------------------
        # MERGE ADJACENT WINDOWS
        # ----------------------------------------------------

        merged = []

        for start, end, slot_score in candidate_slots:

            if merged:

                previous = merged[-1]

                if start <= previous[1]:

                    merged[-1] = (
                        previous[0],
                        max(
                            previous[1],
                            end
                        ),
                        max(
                            previous[2],
                            slot_score
                        )
                    )

                    continue


            merged.append(
                (
                    start,
                    end,
                    slot_score
                )
            )


        # ----------------------------------------------------
        # RESPONSE WINDOWS
        # ----------------------------------------------------

        for start, end, slot_score in merged:

            if slot_score < 25:
                continue


            if slot_score >= 70:

                rating = "Excellent"

            elif slot_score >= 45:

                rating = "Good"

            else:

                rating = "Acceptable"


            duration = int(
                (
                    end - start
                ).total_seconds()
                / 60
            )


            results.append({

                "date":
                    current.isoformat(),

                "start":
                    start.strftime(
                        "%I:%M %p"
                    ).lstrip("0"),

                "end":
                    end.strftime(
                        "%I:%M %p"
                    ).lstrip("0"),

                "startISO":
                    start.isoformat(),

                "endISO":
                    end.isoformat(),

                "durationMinutes":
                    duration,

                "rating":
                    rating,

                "score":
                    slot_score,

                "nakshatra":
                    panchang[
                        "nakshatra"
                    ][
                        "name"
                    ],

                "tithi":
                    panchang[
                        "tithi"
                    ][
                        "name"
                    ],

                "paksha":
                    panchang[
                        "tithi"
                    ][
                        "paksha"
                    ],

                "yoga":
                    panchang[
                        "yoga"
                    ][
                        "name"
                    ],

                "vara":
                    panchang[
                        "vara"
                    ][
                        "name"
                    ],

                "reasons":
                    reasons,

                "avoid":
                    [
                        "Rahu Kalam",
                        "Yamaganda",
                        "Gulika"
                    ]
            })


        current += timedelta(
            days=1
        )


    # Best windows first

    results.sort(
        key=lambda item: (
            -item["score"],
            item["date"],
            item["startISO"]
        )
    )


    return results[:limit]


# ============================================================
# API
# ============================================================

@muhurat_api.route(
    "/api/muhurat",
    methods=["GET"]
)
def muhurat():

    try:

        # ----------------------------------------------------
        # PURPOSE
        # ----------------------------------------------------

        purpose = (
            request.args.get(
                "purpose",
                "work"
            )
            .lower()
            .strip()
        )


        if purpose not in PURPOSES:

            return jsonify({

                "success":
                    False,

                "error":
                    "Invalid purpose",

                "availablePurposes":
                    list(
                        PURPOSES.keys()
                    )

            }), 400


        # ----------------------------------------------------
        # LOCATION
        # ----------------------------------------------------

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


        if latitude is None:

            return jsonify({

                "success":
                    False,

                "error":
                    "latitude is required"

            }), 400


        if longitude is None:

            return jsonify({

                "success":
                    False,

                "error":
                    "longitude is required"

            }), 400


        if not -90 <= latitude <= 90:

            return jsonify({

                "success":
                    False,

                "error":
                    "Invalid latitude"

            }), 400


        if not -180 <= longitude <= 180:

            return jsonify({

                "success":
                    False,

                "error":
                    "Invalid longitude"

            }), 400


        # Validate timezone

        ZoneInfo(
            timezone_name
        )


        # ----------------------------------------------------
        # DATE RANGE
        # ----------------------------------------------------

        from_string = (
            request.args.get(
                "from"
            )
            or
            request.args.get(
                "date"
            )
        )

        to_string = (
            request.args.get(
                "to"
            )
            or
            from_string
        )


        if not from_string:

            return jsonify({

                "success":
                    False,

                "error":
                    "from date is required"

            }), 400


        start_date = datetime.strptime(
            from_string,
            "%Y-%m-%d"
        ).date()


        end_date = datetime.strptime(
            to_string,
            "%Y-%m-%d"
        ).date()


        if end_date < start_date:

            return jsonify({

                "success":
                    False,

                "error":
                    "to date must be on or after from date"

            }), 400


        # Maximum one year

        if (
            end_date - start_date
        ).days > 366:

            return jsonify({

                "success":
                    False,

                "error":
                    "Date range cannot exceed 366 days"

            }), 400


        # ----------------------------------------------------
        # LIMIT
        # ----------------------------------------------------

        limit = request.args.get(
            "limit",
            30,
            type=int
        )

        limit = max(
            1,
            min(
                limit,
                100
            )
        )


        # ----------------------------------------------------
        # CALCULATE
        # ----------------------------------------------------

        windows = calculate_muhurats(

            start_date,

            end_date,

            latitude,

            longitude,

            timezone_name,

            purpose,

            limit

        )


        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return jsonify({

            "success":
                True,

            "engine": {

                "name":
                    "Mauksh Muhurat Engine",

                "version":
                    "1.0",

                "ephemeris":
                    "Swiss Ephemeris",

                "ayanamsa":
                    "Lahiri",

                "baseEngine":
                    "Mauksh Panchang Engine"

            },

            "purpose": {

                "key":
                    purpose,

                "name":
                    PURPOSES[
                        purpose
                    ][
                        "name"
                    ]

            },

            "location": {

                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "timezone":
                    timezone_name

            },

            "from":
                start_date.isoformat(),

            "to":
                end_date.isoformat(),

            "count":
                len(windows),

            "windows":
                windows

        })


    except ValueError as error:

        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 400


    except Exception as error:

        return jsonify({

            "success":
                False,

            "error":
                str(error)

        }), 500