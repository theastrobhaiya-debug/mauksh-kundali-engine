from flask import Flask
from api.panchang import panchang_api
from api.transits import transits_api

app = Flask(__name__)

app.register_blueprint(panchang_api)
app.register_blueprint(transits_api)

@app.route("/")
def home():
    return {
        "success": True,
        "service": "Mauksh Panchang Engine",
        "version": "3.0"
    }

@app.route("/health")
def health():
    return {
        "success": True,
        "status": "healthy"
    }