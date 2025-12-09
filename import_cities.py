import csv
from collections import defaultdict

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DB_URL = "mysql+pymysql://root:Lhqlhq120817.@localhost:3306/myhomework?charset=utf8mb4"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)


def generate_city_id(country_id: str, index: int) -> str:

    return f"{country_id}{index:04d}"


def main():
    session = SessionLocal()

    country_map = {}  # key: 2位country_code, value: 3位country_id
    result = session.execute(text("SELECT country_id, country_code FROM countries"))
    for row in result:
        country_map[row.country_code] = row.country_id

    print(f"[INFO] Loaded {len(country_map)} countries from DB")

    existing_cities = {}
    city_counter = defaultdict(int)

    result = session.execute(text("SELECT city_id, name, country_id FROM cities"))
    for row in result:
        key = (row.country_id, row.name.lower())
        existing_cities[key] = row.city_id

        if row.city_id and len(row.city_id) >= 7 and row.city_id[:3] == row.country_id:
            suffix = row.city_id[3:]
            if suffix.isdigit():
                idx = int(suffix)
                if idx > city_counter[row.country_id]:
                    city_counter[row.country_id] = idx

    print(f"[INFO] Loaded {len(existing_cities)} existing cities from DB")

    insert_sql = text("""
        INSERT INTO cities (
            city_id, name, official_name, population, is_capital,
            latitude, longitude, timezone, country_id
        ) VALUES (
            :city_id, :name, :official_name, :population, :is_capital,
            :latitude, :longitude, :timezone, :country_id
        )
    """)

    update_sql = text("""
        UPDATE cities SET
            name = :name,
            official_name = :official_name,
            population = :population,
            is_capital = :is_capital,
            latitude = :latitude,
            longitude = :longitude,
            timezone = :timezone,
            country_id = :country_id
        WHERE city_id = :city_id
    """)

    geonames_file = r"D:\2023201226\database\cities15000.txt"

    batch_inserts = []
    batch_size = 1000

    count_insert = 0
    count_update = 0
    line_count = 0

    with open(geonames_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")

        for row in reader:
            line_count += 1
            if len(row) < 19:
                continue

            original_name = row[1]
            ascii_name = row[2]
            latitude = row[4]
            longitude = row[5]
            feature_class = row[6]
            country_code2 = row[8]
            population = row[14]
            timezone = row[17]

            if feature_class != "P":
                continue

            if country_code2 not in country_map:
                continue

            country_id3 = country_map[country_code2]

            # 处理人口
            try:
                population_val = int(population)
            except ValueError:
                population_val = None

            # 处理经纬度
            try:
                lat_val = float(latitude)
                lon_val = float(longitude)
            except ValueError:
                # 经纬度异常就跳过
                continue

            if ascii_name:
                english_name = ascii_name
            else:
                english_name = original_name

            official_name = original_name if original_name != english_name else None

            key = (country_id3, english_name.lower())

            if key in existing_cities:
                city_id = existing_cities[key]

                session.execute(update_sql, {
                    "city_id": city_id,
                    "name": english_name,
                    "official_name": official_name,
                    "population": population_val,
                    "is_capital": "N",
                    "latitude": lat_val,
                    "longitude": lon_val,
                    "timezone": timezone,
                    "country_id": country_id3,
                })
                count_update += 1

            else:
                city_counter[country_id3] += 1
                idx = city_counter[country_id3]
                city_id = generate_city_id(country_id3, idx)

                batch_inserts.append({
                    "city_id": city_id,
                    "name": english_name,
                    "official_name": official_name,
                    "population": population_val,
                    "is_capital": "N",
                    "latitude": lat_val,
                    "longitude": lon_val,
                    "timezone": timezone,
                    "country_id": country_id3
                })
                count_insert += 1

                if len(batch_inserts) >= batch_size:
                    session.execute(insert_sql, batch_inserts)
                    session.commit()
                    print(f"[INFO] Inserted {len(batch_inserts)} cities (batch), "
                          f"total inserted: {count_insert}, updated: {count_update}")
                    batch_inserts = []

    # 插入最后一批
    if batch_inserts:
        session.execute(insert_sql, batch_inserts)
        session.commit()
        print(f"[INFO] Inserted {len(batch_inserts)} cities (last batch).")

    session.commit()
    session.close()

    print(f"[DONE] Lines read: {line_count}, Inserted: {count_insert}, Updated: {count_update}")


if __name__ == "__main__":
    main()
