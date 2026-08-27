from flask import Blueprint, request, jsonify
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo
from datetime import datetime

location_api = Blueprint(
    "location_api",
    __name__
)

tf = TimezoneFinder()


@location_api.route(
    "/api/location",
    methods=["GET"]
)
def location():

    city = request.args.get(
        "city",
        ""
    ).strip()

    if not city:

        return jsonify({
            "success": False,
            "error": "City is required"
        }), 400

    # This endpoint is intentionally kept
    # separate from the Kundali calculation engine.
    #
    # We will connect a geocoding provider here
    # in the next step so that:
    #
    # Rishikesh -> latitude
    # Rishikesh -> longitude
    # Rishikesh -> timezone
    #
    # The calculation engine will then use
    # those coordinates.

    return jsonify({
        "success": False,
        "city": city,
        "message": "Location provider not connected yet"
    }), 501
