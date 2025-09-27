from flask import Blueprint, render_template, jsonify, request
from app.models import *

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/cities", methods=["GET"])
def cities():
    return jsonify(get_cities())


@bp.route("/map", methods=["GET"])
def map():
    return jsonify(
        {"cities": get_cities(), "routes": get_routes(), "orders": get_orders()}
    )


@bp.route("/date", methods=["POST"])
def date():
    data = request.json
    value = data.get("value", 0)
    new_date = shift_date(shift=value)
    return jsonify({"date": new_date.strftime("%d.%m.%Y")})


@bp.route("/delete", methods=["POST"])
def delete():
    delete_orders()
    return jsonify({"status": "ok"})


@bp.route("/orders", methods=["GET"])
def orders():
    return jsonify(get_orders())


@bp.route("/send", methods=["POST"])
def send():
    data = request.json or []
    create_orders(data)
    return jsonify({"status": "ok"})
