from datetime import datetime, timedelta
import random
from flask import Blueprint, render_template, jsonify, request
from models import *
from services.load_date import load_date, save_date

bp = Blueprint("main", __name__)

# ------------------------
# Генерация заказов
# ------------------------
def generate_orders():
    current_date = load_date()
    date_obj = Date.query.get(current_date)

    if not date_obj:
        date_obj = Date(date=current_date, generated_orders=False, generated_couriers=False)
        db.session.add(date_obj)
        db.session.commit()

    if date_obj.generated_orders:
        return

    cities = City.query.all()

    for _ in range(random.randint(100, 200)):
        city_from, city_to = random.sample(cities, 2)
        order = Order(
            order_from=city_from.city_id,
            order_to=city_to.city_id,
            order_class=random.choice(["Скорый", "Стандарт"]),
            order_date=current_date,
            order_author="system",
            order_weight=random.choice([5, 10, 50, 100])
        )
        db.session.add(order)

    date_obj.generated_orders = True
    db.session.commit()

# ------------------------
# Генерация курьеров
# ------------------------
def generate_couriers():
    current_date = load_date()
    date_obj = Date.query.get(current_date)

    if not date_obj:
        date_obj = Date(date=current_date, generated_orders=False, generated_couriers=False)
        db.session.add(date_obj)
        db.session.commit()

    if date_obj.generated_couriers:
        return

    cities = City.query.all()

    for city_from in cities:
        for city_to in cities:
            orders = Order.query.filter(
                Order.order_from == city_from.city_id,
                Order.order_to == city_to.city_id,
                Order.order_date == date_obj.date
            ).all()

            if not orders:
                continue

            # Разделяем по классам
            fast_orders = [o for o in orders if o.order_class == "Скорый"]
            standard_orders = [o for o in orders if o.order_class == "Стандарт"]

            def assign_orders(order_list, max_speed, max_weight):
                couriers = []
                current_courier = Courier(
                    courier_from=city_from.city_id,
                    courier_to=city_to.city_id,
                    courier_weight=0,
                    courier_max_speed=max_speed
                )
                db.session.add(current_courier)
                couriers.append(current_courier)

                for order in order_list:
                    if order.assignment:
                        continue
                    assigned = False
                    for courier in couriers:
                        if courier.courier_weight + order.order_weight <= max_weight:
                            courier.courier_weight += order.order_weight
                            db.session.add(Assignment(courier=courier, order=order))
                            assigned = True
                            break
                    if not assigned:
                        new_courier = Courier(
                            courier_from=city_from.city_id,
                            courier_to=city_to.city_id,
                            courier_weight=order.order_weight,
                            courier_max_speed=max_speed
                        )
                        db.session.add(new_courier)
                        db.session.add(Assignment(courier=new_courier, order=order))
                        couriers.append(new_courier)

            assign_orders(fast_orders, max_speed=110, max_weight=100)
            assign_orders(standard_orders, max_speed=80, max_weight=500)

    date_obj.generated_couriers = True
    db.session.commit()


# ------------------------
# Генерация маршрутов
# ------------------------
def find_path(courier, route, progress):
    from datetime import datetime, timedelta

    remaining_time_hours = 24
    distance_left = route.route_length * (1 - progress)

    def effective_speed(route_obj):
        couriers_on_route = route_obj.couriers_statuses
        total_weight = sum(c.courier.courier_weight for c in couriers_on_route) + courier.courier_weight

        if courier.courier_weight > route_obj.route_max_weight:
            return 0

        max_speed = min(route_obj.route_max_speed, courier.courier_max_speed)

        if total_weight <= route_obj.route_capacity:
            return max_speed

        speed_factor = route_obj.route_capacity / total_weight
        return max_speed * speed_factor

    current_route = route
    current_progress = progress
    current_city = route.city_to if progress >= 1.0 else route.city_from

    while remaining_time_hours > 0:
        speed = effective_speed(current_route)
        if speed == 0:
            return datetime.now(), current_route, current_progress

        time_to_finish_route = distance_left / speed
        if time_to_finish_route >= remaining_time_hours:
            distance_covered = speed * remaining_time_hours
            new_progress = current_progress + distance_covered / current_route.route_length
            estimated_delivery = datetime.now() + timedelta(hours=24)
            return estimated_delivery, current_route, new_progress

        remaining_time_hours -= time_to_finish_route
        current_city = current_route.city_to if current_city == current_route.city_from else current_route.city_from

        next_routes = current_city.routes_from + current_city.routes_to
        next_routes = [r for r in next_routes if r != current_route]

        if not next_routes:
            estimated_delivery = datetime.now() + timedelta(hours=(24 - remaining_time_hours))
            return estimated_delivery, current_route, 1.0

        current_route = min(next_routes, key=lambda r: r.route_length / effective_speed(r))
        distance_left = current_route.route_length
        current_progress = 0.0

    estimated_delivery = datetime.now() + timedelta(hours=24)
    return estimated_delivery, current_route, current_progress


# ------------------------
# Генерация статусов
# ------------------------
def set_statuses():
    current_date = load_date()
    date_obj = Date.query.get(current_date)
    if not date_obj:
        date_obj = Date(date=current_date)
        db.session.add(date_obj)
        db.session.commit()

    # Курьеры
    for courier in Courier.query.all():
        last_status = CourierStatus.query.filter_by(courier_id=courier.courier_id, date=current_date).order_by(CourierStatus.status_id.desc()).first()
        if last_status:
            current_route = last_status.route
            progress = last_status.courier_current_speed / max(current_route.route_length, 1)
        else:
            current_route = Route.query.filter(
                (Route.route_from == courier.courier_from) &
                (Route.route_to == courier.courier_to)
            ).first()
            progress = 0.0

        estimated_delivery, new_route, new_progress = find_path(courier, current_route, progress)

        courier_status = CourierStatus(
            courier=courier,
            route=new_route,
            date=current_date,
            route_current_capacity=courier.courier_weight,
            courier_current_speed=courier.courier_max_speed * new_progress
        )
        db.session.add(courier_status)

    # Заказы
    for order in Order.query.all():
        if not order.assignment:
            continue
        courier = order.assignment.courier

        last_status = OrderStatus.query.filter_by(order_id=order.order_id, date=current_date).order_by(OrderStatus.status_id.desc()).first()
        if last_status:
            progress = last_status.progress
            current_route = last_status.route
        else:
            current_route = Route.query.filter(
                (Route.route_from == order.city_from.city_id) &
                (Route.route_to == order.city_to.city_id)
            ).first()
            progress = 0.0

        estimated_delivery, new_route, new_progress = find_path(courier, current_route, progress)

        order_status = OrderStatus(
            order=order,
            route=new_route,
            date=current_date,
            status="В пути" if new_progress < 1 else "Доставлен",
            estimated_delivery=estimated_delivery,
            order_delay=0,
            progress=new_progress
        )
        db.session.add(order_status)

    # Статусы маршрутов
    for route in Route.query.all():
        couriers_on_route = CourierStatus.query.filter_by(route=route, date=current_date).all()
        total_weight = sum(c.courier.courier_weight for c in couriers_on_route)
        max_speed = max([c.courier_current_speed for c in couriers_on_route], default=0)

        route_status = RouteStatus(
            route=route,
            date=current_date,
            route_current_capacity=total_weight,
            route_current_speed=max_speed
        )
        db.session.add(route_status)

    db.session.commit()


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/cities", methods=["GET"])
def get_cities():
    cities = [c.city_name for c in City.query.all()]
    return jsonify(cities)


@bp.route("/map", methods=["GET"])
def map():
    routes_data = [
        {
            "routeFrom": [r.city_from.city_lat, r.city_from.city_lon],
            "routeTo": [r.city_to.city_lat, r.city_to.city_lon],
        }
        for r in Route.query.all()
    ]
    cities_data = [
        {"cityName": c.city_name, "cityLat": c.city_lat, "cityLon": c.city_lon}
        for c in City.query.all()
    ]

    orders_data = []
    for o in Order.query.filter(Order.order_author == "user").all():
        status = next((s for s in o.statuses if s.date == load_date()), None)
        if not status:
            continue
        lat = status.route.city_from.city_lat + (status.route.city_to.city_lat - status.route.city_from.city_lat) * status.progress
        lon = status.route.city_from.city_lon + (status.route.city_to.city_lon - status.route.city_from.city_lon) * status.progress
        orders_data.append({
            "orderId": o.order_id,
            "fromName": o.city_from.city_name,
            "toName": o.city_to.city_name,
            "orderLat": lat,
            "orderLon": lon,
        })

    return jsonify({"cities": cities_data, "routes": routes_data, "orders": orders_data})


@bp.route("/date", methods=["POST"])
def date():
    data = request.json
    value = data.get("value", 0)
    new_date = load_date() + timedelta(days=value)
    save_date(new_date)
    return jsonify({"date": load_date().strftime("%d.%m.%Y")})


@bp.route("/step")
def step():
    generate_orders()
    generate_couriers()
    set_statuses()
    return jsonify({"status": "ok"})


@bp.route("/delete", methods=["POST"])
def delete():
    for order in Order.query.filter(Order.order_author == "user").all():
        db.session.delete(order)
    db.session.commit()
    return jsonify({"status": "ok"})


@bp.route("/orders", methods=["GET"])
def get_orders():
    orders_list = []
    for o in Order.query.all():
        status = next((s for s in o.statuses if s.date == load_date()), None)
        if not status:
            continue
        orders_list.append({
            "id": o.order_id,
            "fromName": o.city_from.city_name,
            "toName": o.city_to.city_name,
            "orderClass": o.order_class,
            "weight": o.order_weight,
            "startDate": o.order_date.strftime("%d.%m.%Y"),
            "expectedDate": status.estimated_delivery.strftime("%d.%m.%Y"),
            "status": status.status,
            "delay": status.order_delay,
        })
    return jsonify(orders_list)


@bp.route("/send", methods=["POST"])
def send():
    data = request.json or []
    for o in data:
        city_from = City.query.filter_by(city_name=o.get("fromName")).first()
        city_to = City.query.filter_by(city_name=o.get("toName")).first()
        new_order = Order(
            order_from=city_from.city_id,
            order_to=city_to.city_id,
            order_class=o.get("orderClass"),
            order_date=datetime.strptime(o.get("startDate", datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d"),
            order_author="user",
            order_weight=int(o.get("weight")),
        )
        db.session.add(new_order)
        db.session.commit()
    set_statuses()
    return jsonify({"status": "ok"})
