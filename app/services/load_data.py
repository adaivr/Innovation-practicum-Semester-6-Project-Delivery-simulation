from models import db, City, Route
import pandas as pd
from geopy.distance import great_circle


def load_map():
    cities_csv = pd.read_csv("data/cities.csv")
    routes_csv = pd.read_csv("data/routes.csv")
    if db.session.query(City).count() != len(cities_csv):
        for _, row in cities_csv.iterrows():
            city = City(
                city_name=row["city_name"],
                city_lat=row["city_lat"],
                city_lon=row["city_lon"],
            )
            db.session.add(city)
        db.session.commit()

    if db.session.query(Route).count() != len(routes_csv):
        for _, row in routes_csv.iterrows():
            city_from = City.query.filter_by(city_name=row["route_from"]).first()
            city_to = City.query.filter_by(city_name=row["route_to"]).first()
            if city_from and city_to:
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
