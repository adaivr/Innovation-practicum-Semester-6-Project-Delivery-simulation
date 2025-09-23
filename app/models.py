from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event

db = SQLAlchemy()


class City(db.Model):
    __tablename__ = "cities"

    city_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    city_name = db.Column(db.String, nullable=False)
    city_lat = db.Column(db.Float, nullable=False)
    city_lon = db.Column(db.Float, nullable=False)

    routes_from = db.relationship("Route", back_populates="city_from", foreign_keys="[Route.route_from]")
    routes_to = db.relationship("Route", back_populates="city_to", foreign_keys="[Route.route_to]")

    orders_from = db.relationship("Order", back_populates="city_from", foreign_keys="[Order.order_from]")
    orders_to = db.relationship("Order", back_populates="city_to", foreign_keys="[Order.order_to]")

    couriers_from = db.relationship("Courier", back_populates="city_from", foreign_keys="[Courier.courier_from]")
    couriers_to = db.relationship("Courier", back_populates="city_to", foreign_keys="[Courier.courier_to]")


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

    city_from = db.relationship("City", back_populates="routes_from", foreign_keys=[route_from])
    city_to = db.relationship("City", back_populates="routes_to", foreign_keys=[route_to])
    
    statuses = db.relationship("RouteStatus", back_populates="route", cascade="all, delete-orphan")
    couriers_statuses = db.relationship("CourierStatus", back_populates="route")


class RouteStatus(db.Model):
    __tablename__ = "route_status"

    status_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.route_id"), nullable=False)
    date = db.Column(db.DateTime, db.ForeignKey("dates.date"), nullable=False)
    route_current_capacity = db.Column(db.Integer, default=0)
    route_current_speed = db.Column(db.Float, default=0.0)

    route = db.relationship("Route", back_populates="statuses")
    date_obj = db.relationship("Date", back_populates="routes_statuses")


class Order(db.Model):
    __tablename__ = 'orders'

    order_id = db.Column(db.Integer, primary_key=True)
    order_from = db.Column(db.Integer, db.ForeignKey("cities.city_id"), nullable=False)
    order_to = db.Column(db.Integer, db.ForeignKey("cities.city_id"), nullable=False)
    order_class = db.Column(db.String, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False)
    order_author = db.Column(db.String, nullable=False)
    order_weight = db.Column(db.Integer, nullable=False)

    city_from = db.relationship("City", back_populates="orders_from", foreign_keys=[order_from])
    city_to = db.relationship("City", back_populates="orders_to", foreign_keys=[order_to])
    statuses = db.relationship("OrderStatus", back_populates="order", cascade="all, delete-orphan")
    assignment = db.relationship("Assignment", back_populates="order", foreign_keys="[Assignment.order_id]", uselist=False, cascade="all, delete-orphan")


class OrderStatus(db.Model):
    __tablename__ = 'order_status'

    status_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=False)
    status = db.Column(db.String, nullable=False)
    date = db.Column(db.DateTime, db.ForeignKey("dates.date"), nullable=False)
    estimated_delivery = db.Column(db.DateTime, nullable=False)
    order_delay = db.Column(db.Integer)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.route_id"), nullable=False)
    progress = db.Column(db.Float, nullable=False)

    route = db.relationship("Route")
    order = db.relationship("Order", back_populates="statuses")
    date_obj = db.relationship("Date", back_populates="orders_statuses")


class Courier(db.Model):
    __tablename__ = 'couriers'

    courier_id = db.Column(db.Integer, primary_key=True)
    courier_from = db.Column(db.Integer, db.ForeignKey("cities.city_id"), nullable=False)
    courier_to = db.Column(db.Integer, db.ForeignKey("cities.city_id"), nullable=False)
    courier_weight = db.Column(db.Integer, nullable=False)
    courier_max_speed = db.Column(db.Float, nullable=False)

    city_from = db.relationship("City", back_populates="couriers_from", foreign_keys=[courier_from])
    city_to = db.relationship("City", back_populates="couriers_to", foreign_keys=[courier_to])

    statuses = db.relationship("CourierStatus", back_populates="courier", cascade="all, delete-orphan")
    assignments = db.relationship("Assignment", back_populates="courier", cascade="all, delete-orphan")    


class CourierStatus(db.Model):
    __tablename__ = 'courier_status'

    status_id = db.Column(db.Integer, primary_key=True)
    courier_id = db.Column(db.Integer, db.ForeignKey("couriers.courier_id"), nullable=False)
    route_id = db.Column(db.Integer, db.ForeignKey("routes.route_id"), nullable=False)
    date = db.Column(db.DateTime, db.ForeignKey("dates.date"), nullable=False)
    route_current_capacity = db.Column(db.Integer, nullable=False)
    courier_current_speed = db.Column(db.Float, nullable=False)
    
    route = db.relationship("Route", back_populates="couriers_statuses")
    courier = db.relationship("Courier", back_populates="statuses")
    date_obj = db.relationship("Date", back_populates="couriers_statuses")


class Assignment(db.Model):
    __tablename__ = 'assignments'

    assignment_id = db.Column(db.Integer, primary_key=True)
    courier_id = db.Column(db.Integer, db.ForeignKey("couriers.courier_id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.order_id"), nullable=False)

    courier = db.relationship("Courier", back_populates="assignments")
    order = db.relationship("Order", back_populates="assignment")


class Date(db.Model):
    __tablename__ = 'dates'

    date = db.Column(db.DateTime, primary_key=True)
    generated_orders = db.Column(db.Boolean, default=False)
    generated_couriers = db.Column(db.Boolean, default=False)

    routes_statuses = db.relationship(
        "RouteStatus",
        back_populates="date_obj",
        cascade="all, delete-orphan",
        foreign_keys="[RouteStatus.date]"
    )
    orders_statuses = db.relationship(
        "OrderStatus",
        back_populates="date_obj",
        cascade="all, delete-orphan",
        foreign_keys="[OrderStatus.date]"
    )
    couriers_statuses = db.relationship(
        "CourierStatus",
        back_populates="date_obj",
        cascade="all, delete-orphan",
        foreign_keys="[CourierStatus.date]"
    )


@event.listens_for(Order, "before_delete")
def subtract_order_weight(mapper, connection, order):
    if order.assignment:
        order.assignment.courier.courier_weight -= order.order_weight
        db.session.add(order.assignment.courier)

@event.listens_for(Courier, "after_update")
def clear_courier(mapper, connection, courier):
    if courier.courier_weight == 0:
        db.session.delete(courier)
