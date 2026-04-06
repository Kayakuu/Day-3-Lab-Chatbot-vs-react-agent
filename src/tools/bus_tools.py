import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
BUS_SCHEDULES_PATH = DATA_DIR / "bus_schedules.json"
OPERATORS_PATH = DATA_DIR / "operators.json"

_MISSING_OD_MSG = (
    "Lỗi: Thiếu điểm đi hoặc điểm đến. "
    "Hãy hỏi lại người dùng muốn đi từ đâu đến đâu."
)
_NO_MATCH_MSG = (
    "Không tìm thấy chuyến xe nào khớp với toàn bộ các tiêu chí. "
    "Hãy thông báo cho người dùng và gợi ý họ thay đổi giờ đi, loại xe hoặc mức giá."
)
_OPERATOR_NOT_FOUND_MSG = (
    "Lỗi: Mã nhà xe '{company_id}' không tồn tại trong hệ thống. "
    "Hãy kiểm tra lại thông tin chuyến xe."
)


class SearchBusSchedulesInput(BaseModel):
    origin: str = Field(..., description="Điểm xuất phát (VD: 'Hà Nội').")
    destination: str = Field(..., description="Điểm đến (VD: 'Sa Pa').")
    departure_date: Optional[str] = Field(
        None, description="Ngày khởi hành mong muốn, định dạng YYYY-MM-DD."
    )
    max_price: Optional[int] = Field(
        None, description="Mức giá tối đa người dùng chấp nhận (VND)."
    )
    vehicle_type: Optional[str] = Field(
        None,
        description="Loại xe yêu cầu (VD: 'Sleeper', 'Standard', 'Limousine').",
    )
    min_available_seats: Optional[int] = Field(
        None, description="Số lượng ghế trống tối thiểu cần đặt."
    )


def _load_bus_schedules() -> List[Dict[str, Any]]:
    with BUS_SCHEDULES_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@tool("search_bus_schedules", args_schema=SearchBusSchedulesInput)
def search_bus_schedules(
    origin: str,
    destination: str,
    departure_date: Optional[str] = None,
    max_price: Optional[int] = None,
    vehicle_type: Optional[str] = None,
    min_available_seats: Optional[int] = None,
) -> str:
    """Search and filter available bus trips from the local schedules database.

    Use this whenever the user wants to look up trips, find buses between two
    cities, or filter trips by date, price, vehicle type, or seat availability.
    Origin and destination are required. All other arguments are optional
    filters that are applied conjunctively.

    Returns a JSON-encoded list of matching trip records on success, or a
    Vietnamese fallback message string when inputs are missing or no trip
    matches the criteria.
    """
    if not origin or not origin.strip() or not destination or not destination.strip():
        return _MISSING_OD_MSG

    origin_q = origin.strip().casefold()
    destination_q = destination.strip().casefold()
    vehicle_q = vehicle_type.strip().casefold() if vehicle_type else None

    schedules = _load_bus_schedules()
    matches: List[Dict[str, Any]] = []
    for record in schedules:
        if origin_q not in str(record.get("origin", "")).casefold():
            continue
        if destination_q not in str(record.get("destination", "")).casefold():
            continue
        if departure_date and not str(record.get("departure_time", "")).startswith(
            departure_date
        ):
            continue
        if max_price is not None and record.get("price", 0) > max_price:
            continue
        if vehicle_q and vehicle_q not in str(record.get("vehicle_type", "")).casefold():
            continue
        if (
            min_available_seats is not None
            and record.get("available_seats", 0) < min_available_seats
        ):
            continue
        matches.append(record)

    if not matches:
        return _NO_MATCH_MSG

    return json.dumps(matches, ensure_ascii=False)


def _load_operators() -> Dict[str, Dict[str, Any]]:
    with OPERATORS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


class GetBusOperatorInfoInput(BaseModel):
    company_id: str = Field(
        ..., description="Mã công ty nhà xe (VD: 'COM-101')."
    )


@tool("get_bus_operator_info", args_schema=GetBusOperatorInfoInput)
def get_bus_operator_info(company_id: str) -> str:
    """Look up a bus operator's policies, luggage rules, and amenities by company_id.

    Use this whenever the user asks about cancellation policy, luggage
    allowance, or amenities of a specific bus company. The `company_id` is
    the `COM-xxx` code that appears on the bus records returned by
    `search_bus_schedules`.

    Returns a JSON string with {name, cancellation_policy, luggage_allowance,
    amenities}, or a Vietnamese fallback message when the id is unknown.
    """
    cid = (company_id or "").strip()
    if not cid:
        return _OPERATOR_NOT_FOUND_MSG.format(company_id=company_id)

    operators = _load_operators()
    record = operators.get(cid)
    if not record:
        return _OPERATOR_NOT_FOUND_MSG.format(company_id=cid)

    return json.dumps({"company_id": cid, **record}, ensure_ascii=False)


class BusBookingTools:
    """
    Standard tools for the Bus Booking ReAct Agent. 
    NOTE: The Tool Developer should implement the logic for these methods 
    using the JSON files in the 'data/' directory.
    """
    
    def search_bus(self, origin: str, destination: str) -> str:
        """
        Search for available buses between two cities.
        Returns a list of matching bus records with fields: id, company_name, departure_time, price, available_seats, vehicle_type.
        Example action: search_bus("Hà Nội", "Sa Pa")
        """
        # TODO: Member 2 (Tool Dev) to implement filtering logic here
        return f"Searching for buses from {origin} to {destination}... [TODO: Implement Logic]"

    def check_availability(self, bus_id: str) -> str:
        """
        Check the number of available seats for a specific bus by ID (e.g., VN-001).
        Example action: check_availability("VN-001")
        """
        # TODO: Member 2 (Tool Dev) to implement seat check logic here
        return f"Checking availability for bus {bus_id}... [TODO: Implement Logic]"

    def book_ticket(self, bus_id: str, customer_name: str, seats: int) -> str:
        """
        Book a specified number of seats on a bus for a customer.
        Example action: book_ticket("VN-001", "Nguyen Van A", 2)
        """
        # TODO: Member 2 (Tool Dev) to implement booking registration here
        return f"Booking {seats} seats on {bus_id} for {customer_name}... [TODO: Implement Logic]"

    def get_operator_policy(self, company_name: str) -> str:
        """
        Get the cancellation and luggage policy for a specific bus company.
        Example action: get_operator_policy("Phương Trang")
        """
        # TODO: Member 2 (Tool Dev) to implement policy lookup from JSON here
        return f"Fetching policy for {company_name}... [TODO: Implement Logic]"
