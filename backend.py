from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
from datetime import datetime
import requests
import pandas as pd
import math
from sqlalchemy import text
import pandas as pd
from io import StringIO
from flask import Response
app = Flask(__name__)

# 配置数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Lhqlhq120817.@localhost:3306/myhomework'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'Lhqlhq120817.'

db = SQLAlchemy(app)
jwt = JWTManager(app)

# 定义数据模型
class Region(db.Model):
    __tablename__ = 'regions'
    region_id = db.Column(db.String(2), primary_key=True)
    name = db.Column(db.String(13), nullable=False)

class Country(db.Model):
    __tablename__ = 'countries'
    country_id = db.Column(db.String(3), primary_key=True)
    country_code = db.Column(db.String(2), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    official_name = db.Column(db.String(200))
    population = db.Column(db.Integer)
    area_sq_km = db.Column(db.Numeric(10, 2))
    latitude = db.Column(db.Numeric(8, 5))
    longitude = db.Column(db.Numeric(8, 5))
    timezone = db.Column(db.String(40))
    region_id = db.Column(db.String(2), db.ForeignKey('regions.region_id'), nullable=False)
    region = db.relationship('Region', backref=db.backref('countries', lazy=True))

class City(db.Model):
    __tablename__ = 'cities'
    city_id = db.Column(db.String(7), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    official_name = db.Column(db.String(200))
    population = db.Column(db.Integer)
    is_capital = db.Column(db.String(1), default='N', nullable=False)
    latitude = db.Column(db.Numeric(8, 5))
    longitude = db.Column(db.Numeric(8, 5))
    timezone = db.Column(db.String(40))
    country_id = db.Column(db.String(3), db.ForeignKey('countries.country_id'), nullable=False)
    country = db.relationship('Country', backref=db.backref('cities', lazy=True))

#定义用户模型
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), default='user')

    def __init__(self, username, password, role='user'):
        self.username = username
        self.password = generate_password_hash(password)
        self.role = role

    def check_password(self, password):
        return check_password_hash(self.password, password)

with app.app_context():
    try:
        db.create_all()

        if not User.query.filter_by(username='001').first():
            hashed_password = generate_password_hash('Lhqlhq120817.')
            admin = User(username='001', password=hashed_password, role='admin')
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"初始化数据库时出错: {e}")

# 用户注册接口
@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists!"}), 400

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully!"}), 201

# 用户登录接口
@app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid credentials!"}), 401

    access_token = create_access_token(identity=str(user.user_id))

    return jsonify({"access_token": access_token}), 200

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    return jsonify(message="This is a protected route."), 200

# 查询国家数据
@app.route('/countries', methods=['GET'])
@jwt_required()
def get_countries():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role == 'user':
        countries = db.session.execute("SELECT * FROM countries").fetchall()
        return jsonify([{
            'country_id': c.country_id,
            'name': c.name,
            'official_name': c.official_name,
            'population': c.population,
            'area_sq_km': c.area_sq_km,
            'latitude': c.latitude,
            'longitude': c.longitude,
            'timezone': c.timezone,
            'region_id': c.region_id
        } for c in countries])

    countries = Country.query.all()
    return jsonify([{
        'country_id': c.country_id,
        'name': c.name,
        'official_name': c.official_name,
        'population': c.population,
        'area_sq_km': c.area_sq_km,
        'latitude': c.latitude,
        'longitude': c.longitude,
        'timezone': c.timezone,
        'region_id': c.region_id
    } for c in countries])

# 添加新地区
@app.route('/regions', methods=['POST'])
@jwt_required()
def add_region():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != 'admin':
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.get_json()
    new_region = Region(region_id=data['region_id'], name=data['name'])

    db.session.add(new_region)
    db.session.commit()

    return jsonify({"message": "Region added successfully!"}), 201

# 添加新国家
@app.route('/countries', methods=['POST'])
@jwt_required()
def add_country():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != 'admin':
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.get_json()
    new_country = Country(
        country_id=data['country_id'],
        country_code=data['country_code'],
        name=data['name'],
        official_name=data.get('official_name'),
        population=data.get('population'),
        area_sq_km=data.get('area_sq_km'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        timezone=data.get('timezone'),
        region_id=data['region_id']
    )
    db.session.add(new_country)
    db.session.commit()
    return jsonify({"message": "Country added successfully!"}), 201

# 添加新城市
@app.route('/cities', methods=['POST'])
@jwt_required()
def add_city():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != 'admin':
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.get_json()
    new_city = City(
        city_id=data['city_id'],
        name=data['name'],
        official_name=data.get('official_name'),
        population=data.get('population'),
        is_capital=data.get('is_capital', 'N'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude'),
        timezone=data.get('timezone'),
        country_id=data['country_id']
    )
    db.session.add(new_city)
    db.session.commit()
    return jsonify({"message": "City added successfully!"}), 201

# 获取所有地区
@app.route('/regions', methods=['GET'])
def get_all_regions():
    regions = db.session.execute(text("SELECT region_id, name FROM regions")).fetchall()

    return jsonify([{
        'region_id': r.region_id,
        'region_name': r.name
    } for r in regions])

#根据地区查询国家
@app.route('/regions/<region_id>/countries', methods=['GET'])
def get_countries_by_region(region_id):
    try:
        result = db.session.execute(text("""
            SELECT country_id, name
            FROM countries
            WHERE region_id = :region_id
        """), {'region_id': region_id})

        countries = result.fetchall()

        if not countries:
            return jsonify({"message": "No countries found for the region"}), 404

        return jsonify([{
            'country_id': c.country_id,
            'country_name': c.name
        } for c in countries]), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

# 获取城市信息
@app.route('/cities', methods=['GET'])
def get_cities():
    cities = City.query.all()
    return jsonify([{
        'city_id': c.city_id,
        'city_name': c.name,
        'official_name': c.official_name,
        'population': c.population,
        'is_capital': c.is_capital,
        'latitude': c.latitude,
        'longitude': c.longitude,
        'timezone': c.timezone,
        'country_id': c.country_id
    } for c in cities]), 200

#根据国家查询城市
@app.route('/countries/<country_id>/cities', methods=['GET'])
def get_cities_by_country(country_id):
    try:
        result = db.session.execute(text("""
            SELECT city_id, name, official_name, population, is_capital, latitude, longitude, timezone, country_id
            FROM cities
            WHERE country_id = :country_id
        """), {'country_id': country_id})

        cities = result.fetchall()

        if not cities:
            return jsonify({"message": "No cities found for the country"}), 404

        return jsonify([{
            'city_id': c.city_id,
            'city_name': c.name,
            'official_name': c.official_name,
            'population': c.population,
            'is_capital': c.is_capital,
            'latitude': c.latitude,
            'longitude': c.longitude,
            'timezone': c.timezone,
            'country_id': c.country_id
        } for c in cities]), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500


#查找单个地区
@app.route('/regions/<region_id>', methods=['GET'])
def get_region(region_id):
    region = Region.query.get(region_id)
    if not region:
        return jsonify({"message": "Region not found"}), 404

    return jsonify({
        "region_id": region.region_id,
        "name": region.name
    })

#查找单个国家
@app.route('/countries/<country_id>', methods=['GET'])
def get_country(country_id):
    country = Country.query.get(country_id)
    if not country:
        return jsonify({"message": "Country not found"}), 404

    return jsonify({
        "country_id": country.country_id,
        "country_code": country.country_code,
        "name": country.name,
        "official_name": country.official_name,
        "population": country.population,
        "area_sq_km": float(country.area_sq_km) if country.area_sq_km is not None else None,
        "latitude": float(country.latitude) if country.latitude is not None else None,
        "longitude": float(country.longitude) if country.longitude is not None else None,
        "timezone": country.timezone,
        "region_id": country.region_id
    })

#查找单个城市
@app.route('/cities/<city_id>', methods=['GET'])
def get_city(city_id):
    city = City.query.get(city_id)
    if not city:
        return jsonify({"message": "City not found"}), 404

    return jsonify({
        "city_id": city.city_id,
        "name": city.name,
        "official_name": city.official_name,
        "population": city.population,
        "is_capital": city.is_capital,
        "latitude": float(city.latitude) if city.latitude is not None else None,
        "longitude": float(city.longitude) if city.longitude is not None else None,
        "timezone": city.timezone,
        "country_id": city.country_id
    })

#按名称查找地区
@app.route('/regions/search', methods=['GET'])
def search_regions():
    name = request.args.get('name')
    if not name:
        return jsonify({"message": "Query param 'name' is required"}), 400

    results = Region.query.filter(Region.name.ilike(f"%{name}%")).all()
    return jsonify([
        {"region_id": r.region_id, "name": r.name}
        for r in results
    ])

#按名称查找国家
@app.route('/countries/search', methods=['GET'])
def search_countries():
    name = request.args.get('name')
    if not name:
        return jsonify({"message": "Query param 'name' is required"}), 400

    results = Country.query.filter(Country.name.ilike(f"%{name}%")).all()
    return jsonify([
        {
            "country_id": country.country_id,
            "country_code": country.country_code,
            "name": country.name,
            "official_name": country.official_name,
            "population": country.population,
            "area_sq_km": float(country.area_sq_km) if country.area_sq_km is not None else None,
            "latitude": float(country.latitude) if country.latitude is not None else None,
            "longitude": float(country.longitude) if country.longitude is not None else None,
            "timezone": country.timezone,
            "region_id": country.region_id
        }
        for country in results
    ])

#按名称查找城市
@app.route('/cities/search', methods=['GET'])
def search_cities():
    name = request.args.get('name')
    if not name:
        return jsonify({"message": "Query param 'name' is required"}), 400

    results = City.query.filter(City.name.ilike(f"%{name}%")).all()
    return jsonify([
        {
            "city_id": city.city_id,
            "name": city.name,
            "official_name": city.official_name,
            "population": city.population,
            "is_capital": city.is_capital,
            "latitude": float(city.latitude) if city.latitude is not None else None,
            "longitude": float(city.longitude) if city.longitude is not None else None,
            "timezone": city.timezone,
            "country_id": city.country_id
        }
        for city in results
    ])

#按人口范围搜索城市
@app.route('/cities', methods=['GET'])
def search_cities_by_population():
    min_pop = request.args.get('min_pop', type=int, default=0)
    cities = City.query.filter(City.population >= min_pop).all()

    return jsonify([{
        "city_id": city.city_id,
        "name": city.name,
        "official_name": city.official_name,
        "population": city.population,
        "is_capital": city.is_capital,
        "latitude": float(city.latitude) if city.latitude is not None else None,
        "longitude": float(city.longitude) if city.longitude is not None else None,
        "timezone": city.timezone,
        "country_id": city.country_id
    } for city in cities])

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # 地球半径，单位：千米
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  # 返回距离，单位：千米

#按经纬度查询附近城市（按距离排序）
@app.route('/cities/nearby', methods=['GET'])
def get_nearby_cities():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', type=float, default=10)  # 默认 10 km

    cities = City.query.all()
    nearby_cities = []

    for city in cities:
        distance = haversine(lat, lon, city.latitude, city.longitude)
        if distance <= radius:
            nearby_cities.append({
                'city_id': city.city_id,
                'name': city.name,
                'distance_km': distance,
                'latitude': city.latitude,
                'longitude': city.longitude,
                'country_id': city.country_id
            })

    nearby_cities.sort(key=lambda x: x['distance_km'])

    return jsonify(nearby_cities)

#按时区查询城市
@app.route('/cities', methods=['GET'])
def get_cities_by_timezone():
    timezone = request.args.get('timezone', type=str)
    cities = City.query.filter_by(timezone=timezone).all()

    return jsonify([{
        'city_id': c.city_id,
        'name': c.name,
        'timezone': c.timezone,
        'population': c.population,
        'is_capital': c.is_capital,
        'latitude': c.latitude,
        'longitude': c.longitude,
        'country_id': c.country_id
    } for c in cities])

#时区转换
@app.route('/time/convert', methods=['GET'])
def convert_time():
    city_time = request.args.get('city_time', type=str)  # 格式：'2025-11-24 12:00:00'
    from_timezone = request.args.get('from_timezone', type=str)
    to_timezone = request.args.get('to_timezone', type=str)

    city_time_obj = datetime.strptime(city_time, "%Y-%m-%d %H:%M:%S")

    from_tz = pytz.timezone(from_timezone)
    to_tz = pytz.timezone(to_timezone)

    city_time_obj = from_tz.localize(city_time_obj)
    converted_time = city_time_obj.astimezone(to_tz)

    return jsonify({
        'original_time': city_time_obj.strftime("%Y-%m-%d %H:%M:%S"),
        'converted_time': converted_time.strftime("%Y-%m-%d %H:%M:%S")
    })

#国家统计
@app.route('/countries/statistics', methods=['GET'])
def get_country_statistics():
    region_id = request.args.get('region', type=str)

    countries = Country.query.filter_by(region_id=region_id).all()

    total_population = sum(c.population for c in countries if c.population)
    total_area = sum(c.area_sq_km for c in countries if c.area_sq_km)
    avg_population_density = total_population / total_area if total_area else 0

    return jsonify({
        'region_id': region_id,
        'total_population': total_population,
        'total_area': total_area,
        'avg_population_density': avg_population_density
    })

#城市统计
@app.route('/cities/statistics', methods=['GET'])
def get_city_statistics():
    country_id = request.args.get('country_id', type=str)

    cities = City.query.filter_by(country_id=country_id).all()

    total_population = sum(c.population for c in cities if c.population)
    total_area = sum(c.area_sq_km for c in cities if c.area_sq_km)
    avg_population_density = total_population / total_area if total_area else 0

    return jsonify({
        'country_id': country_id,
        'total_population': total_population,
        'total_area': total_area,
        'avg_population_density': avg_population_density
    })

# 查询国家的货币
@app.route('/countries/<country_id>/currency', methods=['GET'])
def get_currency_by_country(country_id):
    try:
        result = db.session.execute(text("""
            SELECT c.currency_id, c.name, c.symbol
            FROM currencies c
            JOIN currencies_countries cc ON cc.currency_id = c.currency_id
            JOIN countries co ON co.country_id = cc.country_id
            WHERE co.country_id = :country_id
        """), {'country_id': country_id})

        currency = result.fetchone()
        if currency:
            return jsonify({
                "currency_id": currency.currency_id,
                "name": currency.name,
                "symbol": currency.symbol
            }), 200
        else:
            return jsonify({"message": "Currency not found for this country."}), 404

    except Exception as e:
        return jsonify({"message": str(e)}), 500

#按货币查询国家
@app.route('/countries', methods=['GET'])
def get_countries_by_currency():
    currency_id = request.args.get('currency', type=str)

    # 查询使用某个货币的所有国家
    countries = db.session.execute("""
        SELECT co.country_id, co.name AS country_name
        FROM countries co
        JOIN currencies_countries cc ON co.country_id = cc.country_id
        WHERE cc.currency_id = :currency_id
    """, {'currency_id': currency_id}).fetchall()

    if not countries:
        return jsonify({"message": f"No countries found using currency {currency_id}"}), 404

    return jsonify([{
        'country_id': c.country_id,
        'country_name': c.country_name
    } for c in countries])

#货币兑换
@app.route('/currency/convert', methods=['GET'])
def convert_currency():
    from_currency = request.args.get('from_currency', type=str)
    to_currency = request.args.get('to_currency', type=str)
    amount = request.args.get('amount', type=float)

    if not from_currency or not to_currency or not amount:
        return jsonify({"message": "Missing parameters"}), 400

    url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
    response = requests.get(url)

    if response.status_code != 200:
        return jsonify({"message": "Failed to get exchange rates"}), 500

    data = response.json()

    if to_currency not in data['rates']:
        return jsonify({"message": f"Currency {to_currency} not found in exchange rates"}), 404

    converted_amount = amount * data['rates'][to_currency]

    return jsonify({
        'from_currency': from_currency,
        'to_currency': to_currency,
        'amount': amount,
        'converted_amount': converted_amount
    })

# 更新国家信息
@app.route('/countries/<country_id>', methods=['PUT'])
@jwt_required()
def update_country(country_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != 'admin':
        return jsonify({"message": "Access denied! Admins only."}), 403

    country = Country.query.get(country_id)
    if not country:
        return jsonify({"message": "Country not found!"}), 404

    data = request.get_json()
    country.name = data.get('name', country.name)
    country.official_name = data.get('official_name', country.official_name)
    country.population = data.get('population', country.population)
    country.area_sq_km = data.get('area_sq_km', country.area_sq_km)
    country.latitude = data.get('latitude', country.latitude)
    country.longitude = data.get('longitude', country.longitude)
    country.timezone = data.get('timezone', country.timezone)
    country.region_id = data.get('region_id', country.region_id)

    db.session.commit()
    return jsonify({"message": "Country updated successfully!"}), 200

# 更新城市信息
@app.route('/cities/<city_id>', methods=['PUT'])
@jwt_required()
def update_city(city_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != 'admin':
        return jsonify({"message": "Access denied! Admins only."}), 403

    data = request.get_json()
    city = City.query.get(city_id)
    if not city:
        return jsonify({"message": "City not found!"}), 404

    city.name = data.get('name', city.name)
    city.official_name = data.get('official_name', city.official_name)
    city.population = data.get('population', city.population)
    city.is_capital = data.get('is_capital', city.is_capital)
    city.latitude = data.get('latitude', city.latitude)
    city.longitude = data.get('longitude', city.longitude)
    city.timezone = data.get('timezone', city.timezone)
    city.country_id = data.get('country_id', city.country_id)

    db.session.commit()
    return jsonify({"message": "City updated successfully!"})

# 删除国家
@app.route('/countries/<country_id>', methods=['DELETE'])
@jwt_required()
def delete_country(country_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != 'admin':
        return jsonify({"message": "Access denied! Admins only."}), 403

    country = Country.query.get(country_id)
    if not country:
        return jsonify({"message": "Country not found!"}), 404

    db.session.delete(country)
    db.session.commit()
    return jsonify({"message": "Country deleted successfully!"}), 200

# 删除城市
@app.route('/cities/<city_id>', methods=['DELETE'])
@jwt_required()
def delete_city(city_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != 'admin':
        return jsonify({"message": "Access denied! Admins only."}), 403

    city = City.query.get(city_id)
    if not city:
        return jsonify({"message": "City not found!"}), 404

    db.session.delete(city)
    db.session.commit()
    return jsonify({"message": "City deleted successfully!"})

# 删除地区
@app.route('/regions/<region_id>', methods=['DELETE'])
@jwt_required()
def delete_region(region_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if user.role != 'admin':
        return jsonify({"message": "Access denied! Admins only."}), 403

    region = Region.query.get(region_id)
    if not region:
        return jsonify({"message": "Region not found!"}), 404

    db.session.delete(region)
    db.session.commit()

    return jsonify({"message": "Region deleted successfully!"})

#读取csv，批量导入国家数据
@app.route('/import/countries', methods=['POST'])
def import_countries_from_csv():
    file = request.files.get('file')
    if not file:
        return jsonify({"message": "No file provided"}), 400

    try:
        df = pd.read_csv(file)

        for index, row in df.iterrows():
            new_country = Country(
                country_id=row['country_id'],
                country_code=row['country_code'],
                name=row['name'],
                official_name=row.get('official_name', None),
                population=row.get('population', None),
                area_sq_km=row.get('area_sq_km', None),
                latitude=row.get('latitude', None),
                longitude=row.get('longitude', None),
                timezone=row.get('timezone', None),
                region_id=row['region_id']
            )
            db.session.add(new_country)

        db.session.commit()
        return jsonify({"message": "Countries imported successfully!"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error importing countries: {str(e)}"}), 500

#读取csv，批量导入城市数据
@app.route('/import/cities', methods=['POST'])
def import_cities_from_csv():
    file = request.files.get('file')
    if not file:
        return jsonify({"message": "No file provided"}), 400

    try:
        df = pd.read_csv(file)  # 使用 pandas 读取 CSV 文件

        # 假设 CSV 中有这些列：city_id, name, population, is_capital, latitude, longitude, timezone, country_id
        for index, row in df.iterrows():
            new_city = City(
                city_id=row['city_id'],
                name=row['name'],
                population=row.get('population', None),
                is_capital=row.get('is_capital', 'N'),
                latitude=row.get('latitude', None),
                longitude=row.get('longitude', None),
                timezone=row.get('timezone', None),
                country_id=row['country_id']
            )
            db.session.add(new_city)

        db.session.commit()
        return jsonify({"message": "Cities imported successfully!"}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error importing cities: {str(e)}"}), 500

@app.route('/export/countries', methods=['GET'])
def export_countries_to_csv():
    countries = db.session.execute("""
        SELECT country_id, country_code, name, official_name, population, area_sq_km, latitude, longitude, timezone, region_id
        FROM countries
    """).fetchall()

    # 将查询结果转为 DataFrame
    df = pd.DataFrame(countries, columns=['country_id', 'country_code', 'name', 'official_name', 'population', 'area_sq_km', 'latitude', 'longitude', 'timezone', 'region_id'])

    # 将 DataFrame 转换为 CSV 格式
    output = StringIO()
    df.to_csv(output, index=False)

    # 设置文件类型为 CSV
    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=countries.csv"})

#导出城市数据csv
@app.route('/export/cities', methods=['GET'])
def export_cities_to_csv():
    # 查询所有城市
    cities = db.session.execute("""
        SELECT city_id, name, population, is_capital, latitude, longitude, timezone, country_id
        FROM cities
    """).fetchall()

    df = pd.DataFrame(cities, columns=['city_id', 'name', 'population', 'is_capital', 'latitude', 'longitude', 'timezone', 'country_id'])

    output = StringIO()
    df.to_csv(output, index=False)

    output.seek(0)
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=cities.csv"})

if __name__ == '__main__':
    app.run(debug=True)

