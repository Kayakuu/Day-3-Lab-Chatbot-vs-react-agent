import json
import random
import os
from datetime import datetime, timedelta

def generate_bus_data(num_records=100):
    cities = ["Hà Nội", "Sài Gòn", "Đà Nẵng", "Đà Lạt", "Sa Pa", "Nha Trang", "Hải Phòng", "Huế", "Hội An"]
    companies = ["Phương Trang", "Thành Bưởi", "Hải Vân", "Sao Việt", "Hoàng Long", "Gia Nguyễn"]
    vehicle_types = ["Xe giường nằm (Sleeper)", "Xe ghế ngồi (Standard)", "Limousine VIP"]
    
    # Real-world detailed policies for each company
    detailed_policies = {
        "Phương Trang": "Hủy trước 24h hoàn 90%. Hủy từ 12-24h hoàn 50%. Sau 12h không hoàn tiền. Hành lý tối đa 20kg. Miễn phí nước uống và khăn lạnh.",
        "Thành Bưởi": "Miễn phí hủy vé trước 24h. Hủy trong vòng 24h thu phí 50%. Hỗ trợ xe trung chuyển miễn phí trong bán kính 5km. Có chăn đắp và tai nghe.",
        "Sao Việt": "Hủy trước 12h hoàn 80%. Hủy dưới 12h không hoàn tiền. Hỗ trợ đón trả khách tận nơi tại Phố Cổ Hà Nội và trung tâm Sa Pa. Xe đời mới, cổng sạc USB.",
        "Hải Vân": "Hủy trước 4h hoàn vé 90%. Sau 4h không hoàn tiền. Xe hạng thương gia có ghế massage, miễn phí ăn nhẹ và đồ uống cao cấp.",
        "Hoàng Long": "Hủy trước 24h hoàn 90%. Hủy dưới 24h hoàn 70%. Tuyến Bắc Nam bao gồm suất ăn nóng tại các trạm dừng chân riêng của hãng.",
        "Gia Nguyễn": "Hủy trước 2h thu phí 30%. Hỗ trợ đón/trả khách tại Sân bay Đà Nẵng và các khách sạn trung tâm Hội An. Xe sạch sẽ, tài xế thân thiện."
    }
    
    data = []
    
    # Distance in km for time calculation (internally used)
    routes = {
        ("Hà Nội", "Sa Pa"): 320,
        ("Hà Nội", "Đà Nẵng"): 760,
        ("Hà Nội", "Hải Phòng"): 120,
        ("Sài Gòn", "Đà Lạt"): 310,
        ("Sài Gòn", "Nha Trang"): 430,
        ("Đà Nẵng", "Huế"): 100,
        ("Đà Nẵng", "Hội An"): 30,
        ("Sài Gòn", "Đà Nẵng"): 960,
    }

    start_date = datetime(2024, 4, 7, 8, 0, 0)
    
    for i in range(num_records):
        origin = random.choice(cities)
        destination = random.choice([c for c in cities if c != origin])
        
        # Company selection
        if destination == "Sa Pa":
            company_name = "Sao Việt"
        elif destination == "Đà Lạt":
            company_name = "Thành Bưởi"
        elif destination == "Hội An":
            company_name = "Gia Nguyễn"
        else:
            company_name = random.choice(companies)

        vehicle_type = random.choice(vehicle_types)
        distance = routes.get((origin, destination), routes.get((destination, origin), random.randint(50, 500)))
        
        # Speed logic (50-60 km/h)
        speed = random.randint(45, 60)
        duration_hours = distance / speed
        
        # Pricing logic
        base_rate = random.randint(1000, 1200)
        price = base_rate * distance
        
        if "Sleeper" in vehicle_type:
            price += 50000
        elif "Limousine" in vehicle_type:
            price *= 1.4

        # Seat availability
        available_seats = random.randint(0, 40)

        # Time logic
        days_offset = random.randint(0, 5)
        hours_offset = random.randint(0, 23)
        dep_time = start_date + timedelta(days=days_offset, hours=hours_offset)
        arr_time = dep_time + timedelta(hours=duration_hours)

        record_id = f"VN-{i+1:03d}"
        
        record = {
            "id": record_id,
            "company_name": company_name,
            "origin": origin,
            "destination": destination,
            "departure_time": dep_time.strftime("%Y-%m-%d %H:%M"),
            "arrival_time": arr_time.strftime("%Y-%m-%d %H:%M"),
            "price": int(round(price, -3)), # Round to nearest 1000
            "available_seats": available_seats,
            "vehicle_type": vehicle_type,
            "policy": detailed_policies.get(company_name, "Vui lòng liên hệ nhà xe để biết thêm chi tiết.")
        }
        data.append(record)
    
    return data

if __name__ == "__main__":
    records = generate_bus_data(100)
    os.makedirs("data", exist_ok=True)
    with open("data/bus_schedules.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(records)} records in data/bus_schedules.json")
