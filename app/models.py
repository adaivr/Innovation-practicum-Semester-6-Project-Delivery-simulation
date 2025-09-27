import heapq
import math
import pandas as pd
import random
from app.extensions import db
from app.services.handle_date import get_date, update_date, SIMULATION_SPEED
from datetime import datetime
from geopy.distance import great_circle
from collections import deque
from datetime import timedelta


# Описание таблиц базы данных


class City(db.Model):
    __tablename__ = "cities"

    city_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    city_name = db.Column(db.String, nullable=False)
    city_lat = db.Column(db.Float, nullable=False)
    city_lon = db.Column(db.Float, nullable=False)

    routes_from = db.relationship(
        "Route", back_populates="city_from", foreign_keys="[Route.route_from]"
    )
    routes_to = db.relationship(
        "Route", back_populates="city_to", foreign_keys="[Route.route_to]"
    )
    orders_from = db.relationship(
        "Order", back_populates="city_from", foreign_keys="[Order.order_from]"
    )
    orders_to = db.relationship(
        "Order", back_populates="city_to", foreign_keys="[Order.order_to]"
    )
    couriers_from = db.relationship(
        "Courier", back_populates="city_from", foreign_keys="[Courier.courier_from]"
    )
    couriers_to = db.relationship(
        "Courier", back_populates="city_to", foreign_keys="[Courier.courier_to]"
    )


class Route(db.Model):
    __tablename__ = "routes"

    route_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    route_from = db.Column(db.Integer, db.ForeignKey("cities.city_id"), nullable=False)
    route_to = db.Column(db.Integer, db.ForeignKey("cities.city_id"), nullable=False)
    route_max_speed = db.Column(db.Integer)
    route_max_weight = db.Column(db.Integer)
    route_capacity = db.Column(db.Integer)
    route_length = db.Column(db.Float)
    route_points = db.Column(db.JSON)

    city_from = db.relationship(
        "City", back_populates="routes_from", foreign_keys=[route_from]
    )
    city_to = db.relationship(
        "City", back_populates="routes_to", foreign_keys=[route_to]
    )
    route_statuses = db.relationship(
        "RouteStatus", back_populates="route", cascade="all, delete-orphan"
    )
    couriers_statuses = db.relationship("CourierStatus", back_populates="route")


class RouteStatus(db.Model):
    __tablename__ = "route_status"

    status_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.route_id"), nullable=False)
    date = db.Column(db.Date, db.ForeignKey("dates.date"), nullable=False)
    route_curr_max_speed = db.Column(db.Float)

    route = db.relationship("Route", back_populates="route_statuses")
    date_obj = db.relationship("Date", back_populates="routes_statuses")


class Order(db.Model):
    __tablename__ = "orders"

    order_id = db.Column(db.Integer, primary_key=True)
    order_from = db.Column(db.Integer, db.ForeignKey("cities.city_id"), nullable=False)
    order_to = db.Column(db.Integer, db.ForeignKey("cities.city_id"), nullable=False)
    order_class = db.Column(db.String, nullable=False)
    date = db.Column(db.Date, db.ForeignKey("dates.date"), nullable=False)
    order_author = db.Column(db.String, nullable=False)
    order_weight = db.Column(db.Integer, nullable=False)
    estimated_delivery = db.Column(db.Date, nullable=False)

    city_from = db.relationship(
        "City", back_populates="orders_from", foreign_keys=[order_from]
    )
    city_to = db.relationship(
        "City", back_populates="orders_to", foreign_keys=[order_to]
    )
    order_statuses = db.relationship(
        "OrderStatus", back_populates="order", cascade="all, delete-orphan"
    )
    assignment = db.relationship(
        "Assignment",
        back_populates="order",
        foreign_keys="[Assignment.order_id]",
        uselist=False,
        cascade="all, delete-orphan",
    )


class OrderStatus(db.Model):
    __tablename__ = "order_status"

    status_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=False)
    order_status = db.Column(db.String, nullable=False)
    date = db.Column(db.Date, db.ForeignKey("dates.date"), nullable=False)
    delay = db.Column(db.Integer)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.route_id"), nullable=False)
    progress = db.Column(db.Float)

    route = db.relationship("Route")
    order = db.relationship("Order", back_populates="order_statuses")
    date_obj = db.relationship("Date", back_populates="orders_statuses")


class Courier(db.Model):
    __tablename__ = "couriers"

    courier_id = db.Column(db.Integer, primary_key=True)
    courier_from = db.Column(
        db.Integer, db.ForeignKey("cities.city_id"), nullable=False
    )
    courier_to = db.Column(db.Integer, db.ForeignKey("cities.city_id"), nullable=False)
    date = db.Column(db.Date, db.ForeignKey("dates.date"), nullable=False)
    courier_weight = db.Column(db.Integer, nullable=False)
    courier_max_speed = db.Column(db.Float, nullable=False)
    estimated_delivery = db.Column(db.Date, nullable=False)

    city_from = db.relationship(
        "City", back_populates="couriers_from", foreign_keys=[courier_from]
    )
    city_to = db.relationship(
        "City", back_populates="couriers_to", foreign_keys=[courier_to]
    )

    courier_statuses = db.relationship(
        "CourierStatus", back_populates="courier", cascade="all, delete-orphan"
    )
    assignments = db.relationship(
        "Assignment", back_populates="courier", cascade="all, delete-orphan"
    )


class CourierStatus(db.Model):
    __tablename__ = "courier_status"

    status_id = db.Column(db.Integer, primary_key=True)
    courier_id = db.Column(
        db.Integer, db.ForeignKey("couriers.courier_id"), nullable=False
    )
    route_id = db.Column(db.Integer, db.ForeignKey("routes.route_id"), nullable=False)
    progress = db.Column(db.Float)
    date = db.Column(db.Date, db.ForeignKey("dates.date"), nullable=False)
    delay = db.Column(db.Integer)

    route = db.relationship("Route", back_populates="couriers_statuses")
    courier = db.relationship("Courier", back_populates="courier_statuses")
    date_obj = db.relationship("Date", back_populates="couriers_statuses")


class Assignment(db.Model):
    __tablename__ = "assignments"

    assignment_id = db.Column(db.Integer, primary_key=True)
    courier_id = db.Column(
        db.Integer, db.ForeignKey("couriers.courier_id"), nullable=False
    )
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=False)

    courier = db.relationship("Courier", back_populates="assignments")
    order = db.relationship("Order", back_populates="assignment")


class Date(db.Model):
    __tablename__ = "dates"

    date = db.Column(db.Date, primary_key=True)
    generated_orders = db.Column(db.Boolean, default=False)

    routes_statuses = db.relationship(
        "RouteStatus",
        back_populates="date_obj",
        cascade="all, delete-orphan",
        foreign_keys="[RouteStatus.date]",
    )
    orders_statuses = db.relationship(
        "OrderStatus",
        back_populates="date_obj",
        cascade="all, delete-orphan",
        foreign_keys="[OrderStatus.date]",
    )
    couriers_statuses = db.relationship(
        "CourierStatus",
        back_populates="date_obj",
        cascade="all, delete-orphan",
        foreign_keys="[CourierStatus.date]",
    )


# Методы для взаимодействия с базой данных


# Загрузка данных для карты


def update_cities():
    cities_csv = pd.read_csv("data/cities.csv")
    if db.session.query(City).count() != len(cities_csv):
        db.session.query(City).delete()
        for _, row in cities_csv.iterrows():
            city = City(
                city_name=row["city_name"],
                city_lat=row["city_lat"],
                city_lon=row["city_lon"],
            )
            db.session.add(city)
        db.session.commit()


def update_routes():
    routes_csv = pd.read_csv("data/routes.csv")
    if db.session.query(Route).count() != len(routes_csv):
        db.session.query(Route).delete()
        for _, row in routes_csv.iterrows():
            city_from = City.query.filter_by(city_name=row["route_from"]).first()
            city_to = City.query.filter_by(city_name=row["route_to"]).first()
            route = Route(
                route_from=city_from.city_id,
                route_to=city_to.city_id,
                route_max_speed=row["route_max_speed"],
                route_max_weight=row["route_max_weight"],
                route_capacity=row["route_capacity"],
                route_length=great_circle(
                    (city_from.city_lat, city_from.city_lon),
                    (city_to.city_lat, city_to.city_lon),
                ).km,
                route_points=[
                    [city_from.city_lat, city_from.city_lon],
                    [city_to.city_lat, city_to.city_lon],
                ],
            )
            db.session.add(route)
        db.session.commit()


def set_map():
    update_cities()
    update_routes()


# Получение данных для интерфейса


def get_cities():
    cities = [
        {"cityName": city.city_name, "cityLat": city.city_lat, "cityLon": city.city_lon}
        for city in City.query.all()
    ]
    return cities


def get_routes():
    routes = [
        {
            "routeFrom": [route.city_from.city_lat, route.city_from.city_lon],
            "routeTo": [route.city_to.city_lat, route.city_to.city_lon],
        }
        for route in Route.query.all()
    ]
    return routes


def get_orders(author="user"):
    date = get_date()

    query = (
        db.session.query(Order, OrderStatus)
        .join(OrderStatus, Order.order_id == OrderStatus.order_id)
        .filter(Order.order_author == author, OrderStatus.date == date)
    )

    orders_with_status = query.all()

    orders = []
    for order, status in orders_with_status:
        lat = (
            status.route.city_from.city_lat
            + (status.route.city_to.city_lat - status.route.city_from.city_lat)
            * status.progress
        )
        lon = (
            status.route.city_from.city_lon
            + (status.route.city_to.city_lon - status.route.city_from.city_lon)
            * status.progress
        )

        orders.append(
            {
                "orderId": order.order_id,
                "fromName": order.city_from.city_name,
                "toName": order.city_to.city_name,
                "orderClass": order.order_class,
                "weight": order.order_weight,
                "startDate": order.date.strftime("%d.%m.%Y"),
                "expectedDate": order.estimated_delivery.strftime("%d.%m.%Y"),
                "orderLat": lat,
                "orderLon": lon,
                "delay": status.delay,
                "orderStatus": status.order_status,
            }
        )

    return orders


# Создание и удаление заказов


def get_max_speed_by_class(order_class):
    if order_class == "Стандарт":
        return 80
    return 130


def get_max_weight_by_class(order_class):
    if order_class == "Стандарт":
        return 40
    return 5


def effective_speed(route, max_speed, weight, curr_date):
    if weight > route.route_max_weight:
        return 0
    route_status = RouteStatus.query.filter_by(
        route_id=route.route_id, date=curr_date
    ).first()
    return (
        min(
            route_status.route_curr_max_speed,
            max_speed * route_status.route_curr_max_speed / route.route_max_speed,
        )
        / SIMULATION_SPEED
    )


def estimate_delivery(city_from_id, city_to_id, max_speed, weight, curr_date):
    if city_from_id == city_to_id:
        raise ValueError("Delivery source and destination are similar.")

    heap = [(0.0, city_from_id, [])]
    visited = {}

    while heap:
        curr_time, curr_city_id, path = heapq.heappop(heap)

        if curr_city_id in visited and visited[curr_city_id] <= curr_time:
            continue
        visited[curr_city_id] = curr_time

        if curr_city_id == city_to_id:
            estimated_delivery = curr_date + timedelta(days=math.ceil(curr_time / 24))
            return path, estimated_delivery

        routes = Route.query.filter((Route.route_from == curr_city_id)).all()

        for route in routes:
            neighbor_id = route.route_to
            speed = effective_speed(route, max_speed, weight, curr_date)
            if speed <= 0:
                continue

            travel_time = route.route_length / speed
            heapq.heappush(heap, (curr_time + travel_time, neighbor_id, path + [route]))

    raise RuntimeError(
        f"Path does not exist. {city_from_id, city_to_id, max_speed, weight, curr_date}"
    )


def assign_order(order):
    order_class = order.order_class
    max_speed = get_max_speed_by_class(order_class)
    max_weight = get_max_weight_by_class(order_class)
    couriers = Courier.query.filter_by(
        courier_from=order.order_from,
        courier_to=order.order_to,
        date=order.date,
        courier_max_speed=max_speed,
    ).all()

    if order.assignment:
        return
    for courier in couriers:
        if courier.courier_weight + order.order_weight <= max_weight:
            courier.courier_weight += order.order_weight
            assignment = Assignment(courier=courier, order=order)
            db.session.add(assignment)
            db.session.commit()
            return

    courier = Courier(
        courier_from=order.order_from,
        courier_to=order.order_to,
        date=order.date,
        courier_weight=order.order_weight,
        courier_max_speed=max_speed,
        estimated_delivery=order.estimated_delivery,
    )
    db.session.add(courier)
    courier_status = CourierStatus(
        courier=courier,
        route_id=OrderStatus.query.filter_by(order_id=order.order_id, date=order.date)
        .first()
        .route_id,
        date=order.date,
        progress=0.0,
        delay=0,
    )
    db.session.add(courier_status)
    assignment = Assignment(courier_id=courier.courier_id, order_id=order.order_id)
    db.session.add(assignment)
    db.session.commit()


def create_orders(data):
    for order in data:
        city_from = City.query.filter_by(city_name=order.get("fromName")).first()
        city_to = City.query.filter_by(city_name=order.get("toName")).first()
        order_class = order.get("orderClass")
        start_date_str = order.get("startDate", datetime.now().date().isoformat())
        curr_date = get_date()
        order_date = curr_date.fromisoformat(start_date_str)
        route, estimated_delivery = estimate_delivery(
            city_from.city_id,
            city_to.city_id,
            get_max_speed_by_class(order_class),
            get_max_weight_by_class(order_class),
            curr_date,
        )
        new_order = Order(
            order_from=city_from.city_id,
            order_to=city_to.city_id,
            order_class=order_class,
            date=order_date,
            order_author="user",
            order_weight=int(order.get("weight")),
            estimated_delivery=estimated_delivery,
        )
        db.session.add(new_order)
        status = OrderStatus(
            order=new_order,
            order_status="Ожидает",
            date=order_date,
            route_id=route[0].route_id,
            progress=0.0,
        )
        db.session.add(status)
        db.session.commit()
        assign_order(new_order)


def delete_orders(author="user"):
    for order in Order.query.filter_by(order_author=author).all():
        courier = order.assignment.courier
        courier.courier_weight -= order.order_weight
        if courier.courier_weight == 0:
            db.session.delete(courier)
            db.session.commit()
        db.session.delete(order)
    db.session.commit()


# Обновление статусов и симуляция


def courier_arrived(courier, route, progress):
    return courier.courier_to == route.route_to and progress >= 1.0


def move_courier(courier, status):
    if courier_arrived(courier, status.route, status.progress):
        return (
            courier.estimated_delivery + timedelta(days=status.delay),
            status.route,
            status.progress,
        )
    curr_date = status.date
    max_speed = courier.courier_max_speed
    weight = courier.courier_weight
    path = []
    estimated_delivery = courier.estimated_delivery + timedelta(days=status.delay)
    route = status.route
    if route.route_to != courier.courier_to:
        path, estimated_delivery = estimate_delivery(
            route.route_to,
            courier.courier_to,
            max_speed,
            weight,
            curr_date,
        )
    remaining_time = 24.0
    routes = deque(path)
    progress = status.progress
    while remaining_time > 0:
        speed = effective_speed(route, max_speed, weight, curr_date)
        distance = route.route_length * (1 - progress)
        time_to_finish = distance / speed
        if courier.courier_to == route.route_to:
            if time_to_finish >= remaining_time:
                return (
                    curr_date + timedelta(days=math.ceil(time_to_finish / 24)),
                    route,
                    progress + remaining_time * speed / route.route_length,
                )
            return curr_date + timedelta(days=1), route, 1.0
        if time_to_finish > remaining_time:
            return (
                estimated_delivery + timedelta(days=math.ceil(time_to_finish / 24)),
                route,
                progress + remaining_time * speed / route.route_length,
            )
        remaining_time -= time_to_finish
        progress = 0.0
        route = routes.popleft()

    return estimated_delivery, route, progress


def update_couriers_status():
    curr_date = get_date()
    couriers = Courier.query.all()
    for courier in couriers:
        status = CourierStatus.query.filter_by(
            courier_id=courier.courier_id, date=curr_date
        ).first()
        if courier.date >= curr_date:
            if status:
                continue
            route_id = (
                CourierStatus.query.filter_by(
                    courier_id=courier.courier_id, date=courier.date
                )
                .first()
                .route_id
            )
            new_status = CourierStatus(
                courier_id=courier.courier_id,
                route_id=route_id,
                progress=0.0,
                date=curr_date,
                delay=0,
            )
            db.session.add(new_status)
            continue

        if status:
            db.session.delete(status)
            db.session.commit()

        prev_date = curr_date - timedelta(days=1)
        prev_status = CourierStatus.query.filter_by(
            courier_id=courier.courier_id, date=prev_date
        ).first()
        estimated_delivery, new_route, new_progress = move_courier(courier, prev_status)
        new_status = CourierStatus(
            courier_id=courier.courier_id,
            route_id=new_route.route_id,
            date=curr_date,
            progress=new_progress,
            delay=(estimated_delivery - courier.estimated_delivery).days,
        )
        db.session.add(new_status)
    db.session.commit()


def update_routes_status():
    curr_date = get_date()

    for route in Route.query.all():
        status = RouteStatus.query.filter_by(
            route_id=route.route_id, date=curr_date
        ).first()
        if status:
            db.session.delete(status)
            db.session.commit()

        couriers_statuses = CourierStatus.query.filter_by(
            route_id=route.route_id, date=curr_date
        ).all()

        curr_capacity = 0
        if couriers_statuses:
            curr_capacity = sum(
                courier_status.courier.courier_weight
                * min(courier_status.courier.courier_max_speed, route.route_max_speed)
                for courier_status in couriers_statuses
                if (courier_status.progress > 0.0) and (courier_status.progress < 1.0)
            )

        route_curr_max_speed = route.route_max_speed
        if curr_capacity > route.route_capacity:
            route_curr_max_speed = (
                route.route_max_speed * route.route_capacity / curr_capacity
            )

        route_status = RouteStatus(
            route_id=route.route_id,
            date=curr_date,
            route_curr_max_speed=route_curr_max_speed,
        )
        db.session.add(route_status)

    db.session.commit()


def update_orders_status():
    curr_date = get_date()

    for order in Order.query.all():
        status = OrderStatus.query.filter_by(
            order_id=order.order_id, date=curr_date
        ).first()

        if order.date >= curr_date:
            if status:
                continue

            route_id = (
                OrderStatus.query.filter_by(order_id=order.order_id, date=order.date)
                .first()
                .route_id
            )
            new_status = OrderStatus(
                order_id=order.order_id,
                order_status="Ожидает",
                date=curr_date,
                delay=0,
                route_id=route_id,
                progress=0.0,
            )
            db.session.add(new_status)
            continue

        if status:
            db.session.delete(status)
            db.session.commit()

        courier = order.assignment.courier
        courier_status = CourierStatus.query.filter_by(
            courier_id=courier.courier_id, date=curr_date
        ).first()
        progress = courier_status.progress
        status_str = "В пути"
        if (courier_status.route.route_to == order.order_to) and progress >= 1.0:
            status_str = "Доставлен"

        delay = (
            order.estimated_delivery - courier.estimated_delivery
        ).days + courier_status.delay

        new_status = OrderStatus(
            order_id=order.order_id,
            order_status=status_str,
            date=curr_date,
            route_id=courier_status.route_id,
            progress=progress,
            delay=max(0, delay),
        )
        db.session.add(new_status)
    db.session.commit()


def generate_orders(number=10):
    curr_date = get_date()

    date_obj = db.session.get(Date, curr_date)
    if not date_obj:
        date_obj = Date(date=curr_date, generated_orders=False)
        db.session.add(date_obj)
        db.session.commit()

    if date_obj.generated_orders:
        return
    date_obj.generated_orders = True

    cities = City.query.all()

    for _ in range(random.randint(number, number * 2)):
        city_from, city_to = random.sample(cities, 2)
        if city_from == city_to:
            continue

        order_class = random.choice(["Скорая", "Стандарт"])
        route, estimated_delivery = estimate_delivery(
            city_from.city_id,
            city_to.city_id,
            get_max_speed_by_class(order_class),
            get_max_weight_by_class(order_class),
            curr_date,
        )
        order = Order(
            order_from=city_from.city_id,
            order_to=city_to.city_id,
            order_class=order_class,
            date=curr_date,
            order_author="system",
            order_weight=random.choice([1, 2, 3, 4, 5]),
            estimated_delivery=estimated_delivery,
        )
        db.session.add(order)
        status = OrderStatus(
            order=order,
            order_status="Ожидает",
            date=curr_date,
            route_id=route[0].route_id,
            progress=0.0,
        )
        db.session.add(status)
        db.session.commit()
        assign_order(order)


def shift_date(shift=1):
    # generate_orders(2)
    new_date = update_date(get_date(), shift=shift)
    update_couriers_status()
    update_routes_status()
    update_orders_status()
    return new_date
