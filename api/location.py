from flask import Blueprint, request, jsonify
from timezonefinder import TimezoneFinder

from api.geocoder import search_location


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

    try:

        results = search_location(city)

        if not results:

            return jsonify({
                "success": False,
                "error": "Location not found"
            }), 404

        locations = []

        for item in results:

            latitude = item[
                "latitude"
            ]

            longitude = item[
                "longitude"
            ]

            timezone_name = tf.timezone_at(
                lat=latitude,
                lng=longitude
            )

            locations.append({

                "display_name":
                    item["display_name"],

                "city":
                    item["city"],

                "state":
                    item["state"],

                "country":
                    item["country"],

                "country_code":
                    item["country_code"],

                "latitude":
                    latitude,

                "longitude":
                    longitude,

                "timezone":
                    timezone_name

            })

        return jsonify({

            "success": True,

            "query": city,

            "locations":
                locations

        })

    except Exception as error:

        return jsonify({

            "success": False,

            "error":
                str(error)

        }), 500
