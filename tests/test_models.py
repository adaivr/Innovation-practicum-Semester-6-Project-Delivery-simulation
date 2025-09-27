import math
import pandas as pd
import unittest
from datetime import date, timedelta
from flask import Flask
from flask_testing import TestCase
from unittest import mock

from app.extensions import db
import app.models as models


class TestModels(TestCase):

    def create_app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        db.init_app(app)
        return app

    def setUp(self):
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.close()
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    # Считаем, что handle_date валиден

    # Вспомогательные функции

    def _create_simple_map(self):
        """
        Создание простой карты
        Расстояние между городами одинаковое
        Дороги между городами A и C имеют меньшую максимальную скорость и максимальный вес
        """
        city_1 = models.City(city_name="A", city_lat=10.0, city_lon=20.0)
        city_2 = models.City(city_name="B", city_lat=20.0, city_lon=20.0)
        city_3 = models.City(city_name="C", city_lat=15.0, city_lon=30.0)
        cities = [city_1, city_2, city_3]
        db.session.add_all(cities)
        db.session.commit()

        routes = []
        for city_from in cities:
            for city_to in cities:
                if city_from == city_to:
                    continue
                speed = 130
                weight = 40
                if city_to != city_2 and city_from != city_2:
                    speed = 80
                    weight = 20
                route = models.Route(
                    city_from=city_from,
                    city_to=city_to,
                    route_max_speed=speed,
                    route_max_weight=weight,
                    route_capacity=3200,
                    route_length=100.0,
                    route_points=[
                        [city_from.city_lat, city_from.city_lon],
                        [city_to.city_lat, city_to.city_lon],
                    ],
                )
                db.session.add(route)
                routes.append(route)
        db.session.commit()
        return cities, routes

    # Проверка таблиц

    def test_city_and_route(self):
        with self.app.app_context():
            cities, _ = self._create_simple_map()
            city_A = cities[0]
            city_B = cities[1]
            route_AB = models.Route.query.filter_by(
                city_to=city_A, city_from=city_B
            ).first()
            self.assertEqual(route_AB.city_to.city_name, "A")
            self.assertEqual(route_AB.city_from.city_name, "B")

    def test_order_and_status(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            date_obj = models.Date(date=models.get_date(), generated_orders=False)
            db.session.add(date_obj)
            db.session.commit()

            # Заказ из A в B
            order = models.Order(
                city_from=cities[0],
                city_to=cities[1],
                order_class="Стандарт",
                date=date_obj.date,
                order_author="tester",
                order_weight=5,
                estimated_delivery=date_obj.date,
            )
            db.session.add(order)
            db.session.commit()

            # Статус заказа
            status = models.OrderStatus(
                order=order,
                order_status="Ожидает",
                date=date_obj.date,
                route=routes[0],
                progress=0.0,
            )
            db.session.add(status)
            db.session.commit()

            self.assertEqual(order.city_from.city_name, "A")
            self.assertEqual(status.order.city_from, cities[0])
            self.assertEqual(status.order_status, "Ожидает")
            self.assertEqual(date_obj.date, date_obj.date)

    def test_courier_and_assignment(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            date_obj = models.Date(date=date.today(), generated_orders=False)
            db.session.add(date_obj)
            db.session.commit()

            # Заказ из A в B
            order = models.Order(
                city_from=cities[0],
                city_to=cities[1],
                order_class="Стандарт",
                date=date_obj.date,
                order_author="tester",
                order_weight=5,
                estimated_delivery=date_obj.date,
            )
            db.session.add(order)
            db.session.commit()

            # Курьер
            courier = models.Courier(
                city_from=cities[0],
                city_to=cities[1],
                date=date_obj.date,
                courier_weight=5,
                courier_max_speed=80,
                estimated_delivery=date_obj.date,
            )
            db.session.add(courier)
            db.session.commit()

            # Назначение курьера
            assignment = models.Assignment(
                courier=courier,
                order=order,
            )
            db.session.add(assignment)
            db.session.commit()

            self.assertEqual(assignment.courier, courier)
            self.assertEqual(assignment.order, order)
            self.assertEqual(assignment.courier.city_from.city_name, "A")
            self.assertEqual(assignment.order.city_to.city_name, "B")

    # Загрузка данных для карты

    def test_set_map(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()

            # Подменные таблицы
            cities_df = pd.DataFrame(
                [
                    {
                        "city_name": city.city_name,
                        "city_lat": city.city_lat,
                        "city_lon": city.city_lon,
                    }
                    for city in cities
                ]
            )
            routes_df = pd.DataFrame(
                [
                    {
                        "route_from": route.city_from.city_name,
                        "route_to": route.city_to.city_name,
                        "route_max_speed": route.route_max_speed,
                        "route_max_weight": route.route_max_weight,
                        "route_capacity": route.route_capacity,
                    }
                    for route in routes
                ]
            )
            db.session.query(models.City).delete()
            db.session.commit()

            with mock.patch(
                "app.models.pd.read_csv", side_effect=[cities_df, routes_df]
            ):
                models.set_map()

            db_cities = models.City.query.all()
            db_routes = models.Route.query.all()

            self.assertEqual(len(db_cities), len(cities))
            self.assertEqual(len(db_routes), len(routes))

            city_names_db = {c.city_name for c in db_cities}
            city_names_src = {c.city_name for c in cities}
            self.assertEqual(city_names_db, city_names_src)

            route_pairs_db = {
                (r.city_from.city_name, r.city_to.city_name) for r in db_routes
            }
            route_pairs_src = {
                (r.city_from.city_name, r.city_to.city_name) for r in routes
            }
            self.assertEqual(route_pairs_db, route_pairs_src)

    # Получение данных для интерфейса

    def test_get_orders(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            city_A = cities[0]
            city_B = cities[1]
            route_AB = models.Route.query.filter_by(
                city_from=city_A, city_to=city_B
            ).first()
            order = models.Order(
                city_from=city_A,
                city_to=city_B,
                order_class="Стандарт",
                date=curr_date,
                order_author="tester",
                order_weight=5,
                estimated_delivery=curr_date,
            )
            db.session.add(order)
            db.session.commit()

            status = models.OrderStatus(
                order=order,
                order_status="Ожидает",
                date=curr_date,
                route=route_AB,
                progress=0.5,
                delay=0,
            )
            db.session.add(status)
            db.session.commit()

            orders = models.get_orders(author="tester")

            self.assertEqual(len(orders), 1)
            order_data = orders[0]
            self.assertEqual(order_data["orderId"], order.order_id)
            self.assertEqual(order_data["fromName"], city_A.city_name)
            self.assertEqual(order_data["toName"], city_B.city_name)
            self.assertEqual(order_data["orderClass"], order.order_class)
            self.assertEqual(order_data["weight"], order.order_weight)
            self.assertEqual(order_data["startDate"], order.date.strftime("%d.%m.%Y"))
            self.assertEqual(
                order_data["expectedDate"],
                order.estimated_delivery.strftime("%d.%m.%Y"),
            )
            self.assertAlmostEqual(
                order_data["orderLat"], (city_A.city_lat + city_B.city_lat) / 2
            )
            self.assertAlmostEqual(
                order_data["orderLon"], (city_A.city_lon + city_B.city_lon) / 2
            )
            self.assertEqual(order_data["delay"], status.delay)
            self.assertEqual(order_data["orderStatus"], status.order_status)

    # Создание и удаление заказов

    def test_effective_speed(self):
        with self.app.app_context():
            cities, _ = self._create_simple_map()
            curr_date = date.today()

            city_A = cities[0]
            city_B = cities[1]
            city_C = cities[2]
            route_AB = models.Route.query.filter_by(
                city_to=city_B, city_from=city_A
            ).first()
            route_AC = models.Route.query.filter_by(
                city_to=city_C, city_from=city_A
            ).first()

            route_AB_status = models.RouteStatus(
                route=route_AB,
                date=curr_date,
                route_curr_max_speed=route_AB.route_max_speed - 5,
            )
            db.session.add(route_AB_status)
            route_AC_status = models.RouteStatus(
                route=route_AC,
                date=curr_date,
                route_curr_max_speed=route_AC.route_max_speed - 5,
            )
            db.session.add(route_AC_status)
            db.session.commit()

            weight = 40

            # Вес больше допустимого
            max_speed = 80
            speed = models.effective_speed(
                route_AC,
                max_speed=max_speed,
                weight=weight,
                curr_date=curr_date,
            )
            self.assertEqual(speed, 0)

            # Вес в пределах допустимого, скорость больше допустимого
            max_speed = 130
            expected_speed = (
                min(
                    route_AB_status.route_curr_max_speed,
                    max_speed
                    * route_AB_status.route_curr_max_speed
                    / route_AB.route_max_speed,
                )
                / models.SIMULATION_SPEED
            )
            speed = models.effective_speed(
                route_AB, max_speed=max_speed, weight=weight, curr_date=curr_date
            )
            self.assertEqual(speed, expected_speed)

            # Вес в пределах допустимого, скорость меньше допустимого
            max_speed = 80
            expected_speed = (
                max_speed
                * route_AB_status.route_curr_max_speed
                / route_AB.route_max_speed
                / models.SIMULATION_SPEED
            )
            speed = models.effective_speed(
                route_AB,
                max_speed=max_speed,
                weight=route_AB.route_max_weight,
                curr_date=curr_date,
            )
            self.assertEqual(speed, expected_speed)

    def test_estimate_delivery(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            city_A = cities[0]
            city_B = cities[1]
            city_C = cities[2]
            route_AB = models.Route.query.filter_by(
                city_to=city_B, city_from=city_A
            ).first()
            route_AC = models.Route.query.filter_by(
                city_to=city_C, city_from=city_A
            ).first()
            route_BC = models.Route.query.filter_by(
                city_to=city_C, city_from=city_B
            ).first()

            # Пустые дороги
            for route in routes:
                db.session.add(
                    models.RouteStatus(
                        route_id=route.route_id,
                        date=curr_date,
                        route_curr_max_speed=route.route_max_speed,
                    )
                )
            db.session.commit()

            # Совпадают точки начала и конца
            with self.assertRaises(ValueError):
                models.estimate_delivery(
                    city_A.city_id,
                    city_A.city_id,
                    max_speed=100,
                    weight=10,
                    curr_date=date.today(),
                )

            # Дорога по прямой
            weight = 5
            max_speed = 130
            path, estimated = models.estimate_delivery(
                city_from_id=city_A.city_id,
                city_to_id=city_C.city_id,
                max_speed=max_speed,
                weight=weight,
                curr_date=curr_date,
            )
            self.assertEqual(path, [route_AC])
            self.assertEqual(
                estimated,
                curr_date
                + timedelta(
                    days=math.ceil(
                        route_AC.route_length / route_AC.route_max_speed * models.SIMULATION_SPEED / 24
                    )
                ),
            )

            # Дорога через B
            weight = 40
            max_speed = 80
            path, estimated = models.estimate_delivery(
                city_from_id=city_A.city_id,
                city_to_id=city_C.city_id,
                max_speed=max_speed,
                weight=weight,
                curr_date=curr_date,
            )
            self.assertEqual(path, [route_AB, route_BC])
            self.assertEqual(
                estimated,
                curr_date
                + timedelta(
                    days=math.ceil(
                        (route_AB.route_length + route_BC.route_length)
                        / max_speed
                        * models.SIMULATION_SPEED
                        / 24
                    )
                ),
            )

            # Путь отсутствует
            weight = 80
            max_speed = 80
            with self.assertRaises(RuntimeError):
                models.estimate_delivery(
                    city_from_id=city_A.city_id,
                    city_to_id=city_C.city_id,
                    max_speed=max_speed,
                    weight=weight,
                    curr_date=curr_date,
                )

    def test_assign_order(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            city_A = cities[0]
            city_B = cities[1]
            route_AB = models.Route.query.filter_by(
                city_to=city_B, city_from=city_A
            ).first()

            # Пустые дороги
            for route in routes:
                db.session.add(
                    models.RouteStatus(
                        route_id=route.route_id,
                        date=curr_date,
                        route_curr_max_speed=route.route_max_speed,
                    )
                )
            db.session.commit()

            # Заказы
            light_order = models.Order(
                city_from=city_A,
                city_to=city_B,
                order_class="Стандарт",
                date=curr_date,
                order_author="tester",
                order_weight=10,
                estimated_delivery=curr_date,
            )
            medium_order = models.Order(
                city_from=city_A,
                city_to=city_B,
                order_class="Стандарт",
                date=curr_date,
                order_author="tester",
                order_weight=20,
                estimated_delivery=curr_date,
            )
            heavy_order = models.Order(
                city_from=city_A,
                city_to=city_B,
                order_class="Стандарт",
                date=curr_date,
                order_author="tester",
                order_weight=35,
                estimated_delivery=curr_date,
            )
            db.session.add(light_order)
            db.session.add(medium_order)
            db.session.add(heavy_order)
            db.session.commit()

            for order in [light_order, medium_order, heavy_order]:
                order_status = models.OrderStatus(
                    order=order,
                    order_status="Ожидает",
                    date=curr_date,
                    delay=0,
                    route=route_AB,
                    progress=0.0,
                )
                db.session.add(order_status)
            db.session.commit()

            # Новый курьер
            models.assign_order(light_order)
            light_assignment = models.Assignment.query.filter_by(
                order_id=light_order.order_id
            ).first()
            self.assertIsNotNone(light_assignment)
            self.assertEqual(light_assignment.order.order_id, light_order.order_id)
            self.assertEqual(
                light_assignment.courier.courier_weight, light_order.order_weight
            )

            courier = models.Courier(
                city_from=city_A,
                city_to=city_B,
                date=curr_date,
                courier_weight=0,
                courier_max_speed=models.get_max_speed_by_class("Стандарт"),
                estimated_delivery=curr_date,
            )
            db.session.add(courier)
            db.session.commit()

            # Существующий курьер
            models.assign_order(heavy_order)
            models.assign_order(medium_order)
            heavy_assignment = models.Assignment.query.filter_by(
                order_id=heavy_order.order_id
            ).first()
            medium_assignment = models.Assignment.query.filter_by(
                order_id=medium_order.order_id
            ).first()
            self.assertIsNotNone(heavy_assignment)
            self.assertIsNotNone(medium_assignment)
            self.assertEqual(heavy_assignment.courier.courier_id, courier.courier_id)
            self.assertEqual(
                medium_assignment.courier.courier_id,
                light_assignment.courier.courier_id,
            )
            self.assertEqual(courier.courier_weight, heavy_order.order_weight)
            self.assertEqual(
                medium_assignment.courier.courier_weight,
                light_order.order_weight + medium_order.order_weight,
            )

            # Заказ уже назначен
            prev_assignment_count = models.Assignment.query.count()
            models.assign_order(heavy_order)
            self.assertEqual(models.Assignment.query.count(), prev_assignment_count)

    def test_create_orders(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            city_A = cities[0]
            city_B = cities[1]
            city_C = cities[2]

            # Пустые дороги
            for route in routes:
                db.session.add(
                    models.RouteStatus(
                        route_id=route.route_id,
                        date=curr_date,
                        route_curr_max_speed=route.route_max_speed,
                    )
                )
            db.session.commit()

            orders_data = [
                {
                    "fromName": city_A.city_name,
                    "toName": city_B.city_name,
                    "orderClass": "Стандарт",
                    "startDate": (curr_date + timedelta(days=2)).isoformat(),
                    "weight": 5,
                },
                {
                    "fromName": city_B.city_name,
                    "toName": city_C.city_name,
                    "orderClass": "Скорая",
                    "startDate": curr_date.isoformat(),
                    "weight": 2,
                },
            ]

            models.create_orders(orders_data)
            db_orders = models.Order.query.filter_by(order_author="user").all()
            self.assertEqual(len(db_orders), len(orders_data))

            for order_data in orders_data:
                order = models.Order.query.filter_by(
                    order_from=models.City.query.filter_by(
                        city_name=order_data["fromName"]
                    )
                    .first()
                    .city_id,
                    order_to=models.City.query.filter_by(city_name=order_data["toName"])
                    .first()
                    .city_id,
                ).first()
                self.assertIsNotNone(order)
                self.assertEqual(order.order_class, order_data["orderClass"])
                self.assertEqual(order.order_weight, order_data["weight"])

                status = models.OrderStatus.query.filter_by(
                    order_id=order.order_id
                ).first()
                self.assertIsNotNone(status)
                self.assertEqual(status.order_status, "Ожидает")
                self.assertEqual(status.progress, 0.0)

                assignment = models.Assignment.query.filter_by(
                    order_id=order.order_id
                ).first()
                self.assertIsNotNone(assignment)
                self.assertEqual(assignment.order.order_id, order.order_id)
                self.assertIsNotNone(assignment.courier)

    def test_delete_orders(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            city_A = cities[0]
            city_B = cities[1]
            route_AB = models.Route.query.filter_by(
                city_to=city_B, city_from=city_A
            ).first()

            # Заказы
            tester_order = models.Order(
                city_from=city_A,
                city_to=city_B,
                order_class="Стандарт",
                date=curr_date,
                order_author="tester",
                order_weight=5,
                estimated_delivery=curr_date,
            )
            system_order = models.Order(
                city_from=city_A,
                city_to=city_B,
                order_class="Стандарт",
                date=curr_date,
                order_author="system",
                order_weight=5,
                estimated_delivery=curr_date,
            )
            db.session.add(tester_order)
            db.session.add(system_order)
            db.session.commit()

            tester_status = models.OrderStatus(
                order=tester_order,
                order_status="Ожидает",
                date=curr_date,
                route=route_AB,
                progress=0.0,
            )
            system_status = models.OrderStatus(
                order=system_order,
                order_status="Ожидает",
                date=curr_date,
                route=route_AB,
                progress=0.0,
            )
            db.session.add(tester_status)
            db.session.add(system_status)
            db.session.commit()

            # Курьеры
            tester_courier = models.Courier(
                city_from=city_A,
                city_to=city_B,
                date=curr_date,
                courier_weight=0,
                courier_max_speed=models.get_max_speed_by_class("Стандарт"),
                estimated_delivery=curr_date,
            )
            system_courier = models.Courier(
                city_from=city_A,
                city_to=city_B,
                date=curr_date,
                courier_weight=0,
                courier_max_speed=models.get_max_speed_by_class("Стандарт"),
                estimated_delivery=curr_date,
            )
            db.session.add(tester_courier)
            db.session.add(system_courier)
            db.session.commit()

            tester_courier_status = models.CourierStatus(
                courier=tester_courier,
                route=route_AB,
                date=curr_date,
                progress=0.0,
                delay=0,
            )
            system_courier_status = models.CourierStatus(
                courier=system_courier,
                route=route_AB,
                date=curr_date,
                progress=0.0,
                delay=0,
            )
            db.session.add(tester_courier_status)
            db.session.add(system_courier_status)
            db.session.commit()

            # Назначения
            tester_assignment = models.Assignment(
                order=tester_order, courier=tester_courier
            )
            system_assignment = models.Assignment(
                order=system_order, courier=system_courier
            )
            db.session.add(tester_assignment)
            db.session.add(system_assignment)
            db.session.commit()

            # Вес курьера
            tester_courier.courier_weight += tester_order.order_weight
            system_courier.courier_weight += system_order.order_weight

            db.session.commit()

            models.delete_orders(author="tester")

            self.assertEqual(models.Order.query.all(), [system_order])
            self.assertEqual(models.OrderStatus.query.all(), [system_status])
            self.assertEqual(models.Assignment.query.all(), [system_assignment])
            self.assertEqual(models.Courier.query.all(), [system_courier])
            self.assertEqual(models.CourierStatus.query.all(), [system_courier_status])

    # Обновление статусов

    def test_move_courier(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            route = routes[0]
            route_status = models.RouteStatus(
                route=route, 
                date=curr_date, 
                route_curr_max_speed=route.route_max_speed
            )
            db.session.add(route_status)
            db.session.commit()

            # Курьер в начале маршрута
            courier1 = models.Courier(
                city_from=cities[0],
                city_to=cities[1],
                date=curr_date,
                courier_weight=5,
                courier_max_speed=80,
                estimated_delivery=curr_date,
            )
            db.session.add(courier1)
            db.session.commit()

            status1 = models.CourierStatus(
                courier=courier1, 
                route=route, 
                date=curr_date, 
                progress=0.0, 
                delay=0
            )
            db.session.add(status1)
            db.session.commit()

            est_delivery1, route_res1, progress_res1 = models.move_courier(courier1, status1)
            
            self.assertEqual(route_res1, route)
            self.assertGreaterEqual(progress_res1, 0.0)
            self.assertGreaterEqual(est_delivery1, curr_date)

            # Курьер в конце маршрута с задержкой
            courier2 = models.Courier(
                city_from=cities[0],
                city_to=cities[1],
                date=curr_date,
                courier_weight=5,
                courier_max_speed=80,
                estimated_delivery=curr_date,
            )
            db.session.add(courier2)
            db.session.commit()

            status2 = models.CourierStatus(
                courier=courier2, 
                route=route, 
                date=curr_date, 
                progress=1.0, 
                delay=1
            )
            db.session.add(status2)
            db.session.commit()

            est_delivery2, route_res2, progress_res2 = models.move_courier(courier2, status2)
            
            expected_delivery = courier2.estimated_delivery + timedelta(days=status2.delay)
            self.assertEqual(est_delivery2, expected_delivery)
            self.assertEqual(progress_res2, 1.0)
            self.assertEqual(route_res2, route)

            # Курьер в середине маршрута
            courier3 = models.Courier(
                city_from=cities[0],
                city_to=cities[1],
                date=curr_date,
                courier_weight=5,
                courier_max_speed=80,
                estimated_delivery=curr_date,
            )
            db.session.add(courier3)
            db.session.commit()

            status3 = models.CourierStatus(
                courier=courier3, 
                route=route, 
                date=curr_date, 
                progress=0.5, 
                delay=0
            )
            db.session.add(status3)
            db.session.commit()

            est_delivery3, route_res3, progress_res3 = models.move_courier(courier3, status3)
            
            self.assertEqual(route_res3, route)
            self.assertGreaterEqual(progress_res3, 0.5)
            self.assertLessEqual(progress_res3, 1.0)
            self.assertGreaterEqual(est_delivery3, curr_date)

    def test_generate_orders(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            for route in routes:
                db.session.add(
                    models.RouteStatus(
                        route_id=route.route_id,
                        date=curr_date,
                        route_curr_max_speed=route.route_max_speed,
                    )
                )
            db.session.commit()

            models.generate_orders(number=2)

            orders = models.Order.query.filter_by(order_author="system").all()
            self.assertTrue(len(orders) >= 2)
            
            for order in orders:
                self.assertIsNotNone(order.estimated_delivery)
                self.assertIsNotNone(order.order_from)
                self.assertIsNotNone(order.order_to)

    def test_update_couriers_status(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            # Курьер с текущей датой
            courier1 = models.Courier(
                city_from=cities[0],
                city_to=cities[1],
                date=curr_date,
                courier_weight=5,
                courier_max_speed=80,
                estimated_delivery=curr_date,
            )
            db.session.add(courier1)
            db.session.commit()

            db.session.add(
                models.CourierStatus(
                    courier=courier1,
                    route=routes[0],
                    date=courier1.date,
                    progress=0.0,
                    delay=0,
                )
            )

            # Курьер с предыдущей датой
            prev_date = curr_date - timedelta(days=1)
            courier2 = models.Courier(
                city_from=cities[1],
                city_to=cities[2],
                date=prev_date,
                courier_weight=10,
                courier_max_speed=80,
                estimated_delivery=curr_date,
            )
            db.session.add(courier2)
            db.session.commit()

            prev_status = models.CourierStatus(
                courier=courier2, 
                route=routes[0], 
                date=prev_date, 
                progress=0.5, 
                delay=1
            )
            db.session.add(prev_status)
            db.session.commit()

            # Статусы дорог для обеих дат
            for route in routes:
                db.session.add(
                    models.RouteStatus(
                        route_id=route.route_id,
                        date=curr_date,
                        route_curr_max_speed=route.route_max_speed,
                    )
                )
                db.session.add(
                    models.RouteStatus(
                        route_id=route.route_id,
                        date=prev_date,
                        route_curr_max_speed=route.route_max_speed,
                    )
                )

            db.session.commit()
            models.update_couriers_status()

            statuses = models.CourierStatus.query.filter_by(date=curr_date).all()
            self.assertTrue(len(statuses) >= 1)

    def test_update_orders_status(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            # Заказ с предыдущей датой
            order = models.Order(
                city_from=cities[0],
                city_to=cities[1],
                order_class="Стандарт",
                date=curr_date - timedelta(days=1),
                order_author="user",
                order_weight=5,
                estimated_delivery=curr_date,
            )
            db.session.add(order)
            db.session.commit()

            # Курьер для заказа
            courier = models.Courier(
                city_from=cities[0],
                city_to=cities[1],
                date=curr_date,
                courier_weight=5,
                courier_max_speed=80,
                estimated_delivery=curr_date,
            )
            db.session.add(courier)
            db.session.commit()

            assignment = models.Assignment(courier=courier, order=order)
            db.session.add(assignment)
            db.session.commit()

            # Статус курьера
            courier_status = models.CourierStatus(
                courier=courier, 
                route=routes[0], 
                date=curr_date, 
                progress=1.0, 
                delay=0
            )
            db.session.add(courier_status)
            db.session.commit()

            # Статус заказа
            db.session.add(
                models.OrderStatus(
                    order=order,
                    order_status="Ожидает",
                    date=order.date,
                    route_id=routes[0].route_id,
                    progress=0.0,
                )
            )
            db.session.commit()

            # Статусы дорог
            for route in routes:
                db.session.add(
                    models.RouteStatus(
                        route_id=route.route_id,
                        date=curr_date,
                        route_curr_max_speed=route.route_max_speed,
                    )
                )
            db.session.commit()

            models.update_orders_status()

            new_status = models.OrderStatus.query.filter_by(
                date=curr_date, 
                order_id=order.order_id
            ).first()
            
            self.assertIsNotNone(new_status)
            self.assertIn(new_status.order_status, ["В пути", "Доставлен"])

    def test_update_routes_status(self):
        with self.app.app_context():
            cities, routes = self._create_simple_map()
            curr_date = models.get_date()

            # Курьер с большим весом для тестирования влияния на дорогу
            courier = models.Courier(
                city_from=cities[0],
                city_to=cities[1],
                date=curr_date,
                courier_weight=50,
                courier_max_speed=100,
                estimated_delivery=curr_date,
            )
            db.session.add(courier)
            db.session.commit()

            status = models.CourierStatus(
                courier=courier, 
                route=routes[0], 
                date=curr_date, 
                progress=0.5, 
                delay=0
            )
            db.session.add(status)
            db.session.commit()

            models.update_routes_status()

            route_status = models.RouteStatus.query.filter_by(
                route_id=routes[0].route_id, 
                date=curr_date
            ).first()
            
            self.assertIsNotNone(route_status)
            self.assertGreater(route_status.route_curr_max_speed, 0)


if __name__ == "__main__":
    unittest.main()
