import json
import random
from datetime import datetime, timedelta

def generate_bus_data(num_records=50):
    cities = ["Hanoi", "Saigon", "Danang", "Dalat", "Sapa", "Nha Trang", "Hai Phong", "Hue"]
    operators = ["Phuong Trang", "Thanh Buoi", "Hai Van", "Sao Viet", "Hoang Long"]
    bus_types = ["Standard", "Sleeper", "VIP Limousine"]
    
    data = []
    
    # Base prices for routes (rougly)
    prices = {
        ("Hanoi", "Sapa"): 300000,
        ("Hanoi", "Danang"): 600000,
        ("Hanoi", "Hai Phong"): 150000,
        ("Saigon", "Dalat"): 400000,
        ("Saigon", "Nha Trang"): 450000,
        ("Danang", "Hue"): 100000,
        ("Danang", "HoiAn"): 120000,
    }

    start_date = datetime(2024, 4, 7, 8, 0, 0)
    
    for i in range(num_records):
        origin = random.choice(cities)
        destination = random.choice([c for c in cities if c != origin])
        
        # Route-biased operator selection
        if destination == "Sapa":
            operator = "Sao Viet"
        elif destination == "Dalat":
            operator = "Thanh Buoi"
        else:
            operator = random.choice(operators)

        bus_type = random.choice(bus_types)
        
        # Calculate price based on route distance (dummy logic) or random
        base_price = prices.get((origin, destination), prices.get((destination, origin), 250000))
        # Adjust price based on type
        if bus_type == "Sleeper":
            final_price = base_price + 100000
        elif bus_type == "VIP Limousine":
            final_price = base_price * 2
        else:
            final_price = base_price

        # Specific seat availability for edge cases
        if i == 0:
            available_seats = 0 # Sold out
        elif i == 1:
            available_seats = 1 # Last seat
        else:
            available_seats = random.randint(2, 40)

        # Random departure time over next 4 days
        days_offset = random.randint(0, 3)
        hours_offset = random.randint(0, 23)
        departure_time = (start_date + timedelta(days=days_offset, hours=hours_offset)).isoformat()

        bus_id = f"{origin[:2].upper()}-{destination[:2].upper()}-{i+1:02d}"
        
        record = {
            "bus_id": bus_id,
            "operator": operator,
            "origin": origin,
            "destination": destination,
            "bus_type": bus_type,
            "departure_time": departure_time,
            "price": final_price,
            "available_seats": available_seats
        }
        data.append(record)
    
    return data

if __name__ == "__main__":
    records = generate_bus_data(50)
    with open("data/bus_schedules.json", "w") as f:
        json.dump(records, f, indent=2)
    print(f"Generated {len(records)} records in data/bus_schedules.json")
