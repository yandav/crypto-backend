# routes/open_interest.py

from flask import Blueprint, jsonify
from binance_api import get_open_interest_data

open_interest_bp = Blueprint("open_interest", __name__)

@open_interest_bp.route("/api/open_interest", methods=["GET"])
def open_interest():
    data = get_open_interest_data()
    return jsonify({"message": "success", "data": data})
