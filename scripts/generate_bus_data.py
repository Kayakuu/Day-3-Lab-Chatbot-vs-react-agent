import json
import random
import os
from datetime import datetime, timedelta

def load_data():
    with open('data/mock_distances.json', 'r', encoding='utf-8') as f:
        distances = json.load(f)
    with open('data/operators.json', 'r', encoding='utf-8') as f:
        operators = json.load(f)
    return distances, operators

def generate_bus_data(num_records=100):
    distances, operators = load_data()
    vehicle_types = ["Xe giường nằm (Sleeper)", "Xe ghế ngồi (Standard)", "Limousine VIP"]
    
    # Extract all valid routes from distance matrix
    routes = []
    for origin, dests in distances.items():
        for dest, km in dests.items():
            routes.append((origin, dest, km))
            routes.append((dest, origin, km))
            
    operator_keys = list(operators.keys())

    data = []
    start_date = datetime(2024, 4, 7, 8, 0, 0)
    
    for i in range(num_records):
        route = random.choice(routes)
        origin, destination, distance_km = route
        
        company_id = random.choice(operator_keys)

        vehicle_type = random.choice(vehicle_types)
        
        # Speed logic (50-60 km/h)
        speed = random.randint(45, 60)
        duration_hours = distance_km / speed
        
        # Create duration string "Xh Ym"
        dur_h = int(duration_hours)
        dur_m = int((duration_hours - dur_h) * 60)
        duration_str = f"{dur_h}h {dur_m}m"
        
        # Pricing logic
        base_rate = random.randint(1000, 1200)
        price = base_rate * distance_km
        
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
            "company_id": company_id,
            "origin": origin,
            "destination": destination,
            "distance_km": distance_km,
            "departure_time": dep_time.strftime("%Y-%m-%d %H:%M"),
            "arrival_time": arr_time.strftime("%Y-%m-%d %H:%M"),
            "duration": duration_str,
            "price": int(round(price, -3)), 
            "available_seats": available_seats,
            "vehicle_type": vehicle_type
        }
        data.append(record)
    
    return data

if __name__ == "__main__":
    records = generate_bus_data(100)
    os.makedirs("data", exist_ok=True)
    with open("data/bus_schedules.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(records)} records in data/bus_schedules.json")
    print("\n--- SAMPLE RECORD DEMO ---")
    print(json.dumps(records[0], indent=2, ensure_ascii=False))
