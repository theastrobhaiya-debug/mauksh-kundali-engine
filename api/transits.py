from flask import Blueprint, jsonify

transits_api = Blueprint("transits_api", __name__)


@transits_api.route("/api/test-transits", methods=["GET"])
def test_transits():
    return jsonify({
        "success": True,
        "message": "Transits API connected"
    })


@transits_api.route("/api/planetary-positions", methods=["GET"])
def planetary_positions():
    return jsonify({
        "success": True,
        "system": "Vedic Sidereal",
        "ayanamsha": "Lahiri",
        "message": "Planetary positions API connected"
    })


@transits_api.route("/api/upcoming-transits", methods=["GET"])
def upcoming_transits():
    return jsonify({
        "success": True,
        "system": "Vedic Sidereal",
        "ayanamsha": "Lahiri",
        "message": "Upcoming transits API connected"
    })