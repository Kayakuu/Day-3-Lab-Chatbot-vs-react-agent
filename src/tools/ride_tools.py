from typing import Dict, List

POLICIES: Dict[str, str] = {
    "cancellation": "Cancel before 24 hours for a full refund.",
    "late_arrival": "If the driver is more than 15 minutes late, contact support for a free reschedule.",
    "pet_policy": "Small pets are allowed with prior notice; large animals require a special vehicle.",
}

VEHICLE_TYPES: List[Dict[str, str]] = [
    {"name": "Sedan", "capacity": "4 seats", "description": "Economical and comfortable for small groups."},
    {"name": "SUV", "capacity": "7 seats", "description": "Spacious and ideal for families or groups."},
    {"name": "Limousine", "capacity": "9 seats", "description": "Luxury service for premium trips."},
]

ROUTE_DISTANCES: Dict[str, int] = {
    "Hanoi->Sapa": 320,
    "Da Nang->Hue": 100,
    "Hanoi->Ninh Binh": 95,
}

DRIVERS: List[Dict[str, str]] = [
    {"name": "Hung Alpha", "rating": "4.9", "vehicle_type": "7-seater"},
    {"name": "Linh Bravo", "rating": "4.7", "vehicle_type": "4-seater"},
    {"name": "Minh Charlie", "rating": "4.8", "vehicle_type": "9-seater"},
]

PRICE_MULTIPLIER: Dict[str, float] = {
    "Sedan": 12000,
    "SUV": 14000,
    "Limousine": 18500,
    "7-seater": 14000,
    "9-seater": 18500,
    "tunnel": 12000,
    "pass": 11000,
}


def get_policy(policy_name: str) -> str:
    key = policy_name.strip().lower()
    return POLICIES.get(key, "Sorry, I don't have that policy on file.")


def get_vehicle_types() -> str:
    lines = [f"{item['name']} ({item['capacity']}): {item['description']}" for item in VEHICLE_TYPES]
    return "; ".join(lines)


def get_distance(origin: str, destination: str) -> str:
    route_key = f"{origin.strip()}->{destination.strip()}"
    distance = ROUTE_DISTANCES.get(route_key)
    if distance is None:
        return "Distance data not found for this route."
    return f"{distance}km"


def calculate_price(distance: float, vehicle_type: str) -> str:
    vehicle_key = vehicle_type.strip()
    rate = PRICE_MULTIPLIER.get(vehicle_key)
    if rate is None:
        return "Unknown vehicle type for pricing."
    total = int(float(distance) * rate)
    return f"{total:,} VND"


def filter_drivers(min_rating: float, vehicle_type: str) -> str:
    candidates = [driver for driver in DRIVERS
                  if float(driver["rating"]) >= float(min_rating)
                  and vehicle_type.lower() in driver["vehicle_type"].lower()]

    if not candidates:
        return "No matching drivers found."

    formatted = [f"{driver['name']} ({driver['rating']} stars)" for driver in candidates]
    return ", ".join(formatted)


def get_route_details(origin: str, destination: str) -> str:
    route_key = f"{origin.strip()}->{destination.strip()}"
    if route_key == "Da Nang->Hue":
        return "Tunnel: short and toll-based; Pass: scenic, longer, and free."
    if route_key == "Hanoi->Sapa":
        return "Direct highway route, approximately 320km, reliable for weekend travel."
    return "Route details are not available for this pair."


def ask_user(prompt: str) -> str:
    return prompt.strip()
