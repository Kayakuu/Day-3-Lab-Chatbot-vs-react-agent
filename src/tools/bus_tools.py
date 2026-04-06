import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import requests
from langchain_core.tools import tool
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
BUS_SCHEDULES_PATH = DATA_DIR / "bus_schedules.json"
OPERATORS_PATH = DATA_DIR / "operators.json"

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

OPENWEATHER_URL_CURRENT = "https://api.openweathermap.org/data/2.5/weather"
OPENWEATHER_URL_FORECAST = "https://api.openweathermap.org/data/2.5/forecast"
TAVILY_URL = "https://api.tavily.com/search"

EXTERNAL_TIMEOUT_S = 6.0

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
_DATETIME_ERROR_MSG = (
    "Lỗi: Không thể lấy được thời gian hệ thống. "
    "Hãy yêu cầu người dùng cung cấp cụ thể ngày giờ họ muốn đi thay vì nói 'hôm nay'."
)
_WEATHER_NOT_FOUND_MSG = (
    "Lỗi: Không tìm thấy dữ liệu thời tiết cho '{location}'. "
    "Hãy thông báo cho người dùng không thể kiểm tra thời tiết lúc này."
)
_WEATHER_TIMEOUT_MSG = (
    "Lỗi gián đoạn kết nối với trạm thời tiết. "
    "Bỏ qua thông tin thời tiết và tiếp tục hỗ trợ đặt vé."
)
_WEB_NO_RESULTS_MSG = (
    "Không tìm thấy thông tin trên mạng cho truy vấn này. "
    "Hãy báo cho người dùng rằng bạn chỉ là trợ lý đặt vé và không có thông tin ngoài luồng này."
)
_WEB_NETWORK_ERROR_MSG = (
    "Lỗi kết nối công cụ tìm kiếm. "
    "Hãy xin lỗi người dùng và khuyên họ tự tra cứu trên Google."
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


@tool("get_current_datetime")
def get_current_datetime() -> str:
    """Return the current date and time in Vietnam timezone (Asia/Ho_Chi_Minh).

    Call this FIRST whenever the user uses relative time expressions such as
    "hôm nay", "ngày mai", "tối nay", "sắp tới", or "bây giờ", so that other
    tools can be called with a concrete YYYY-MM-DD date.

    Returns a string formatted as 'YYYY-MM-DD HH:MM:SS', or a Vietnamese
    fallback message on failure.
    """
    try:
        return datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return _DATETIME_ERROR_MSG


class GetRouteWeatherInput(BaseModel):
    location: str = Field(
        ..., description="Tên thành phố/tỉnh (VD: 'Đà Lạt', 'Sa Pa')."
    )
    date: Optional[str] = Field(
        None,
        description="Ngày cần xem dự báo (YYYY-MM-DD). Bỏ trống = hôm nay.",
    )


def _format_weather(location: str, date_label: str, payload: Dict[str, Any]) -> str:
    main = payload.get("main", {}) or {}
    weather_list = payload.get("weather") or []
    description = (weather_list[0].get("description") if weather_list else "") or "không rõ"
    temp = main.get("temp")
    humidity = main.get("humidity")
    wind = (payload.get("wind") or {}).get("speed")
    temp_str = f"{temp:.1f}" if isinstance(temp, (int, float)) else "?"
    wind_str = f"{wind:.1f}" if isinstance(wind, (int, float)) else "?"
    humidity_str = f"{humidity}" if humidity is not None else "?"
    return (
        f"{location} ({date_label}): nhiệt độ {temp_str}°C, {description}, "
        f"gió {wind_str} m/s, độ ẩm {humidity_str}%."
    )


@tool("get_route_weather", args_schema=GetRouteWeatherInput)
def get_route_weather(location: str, date: Optional[str] = None) -> str:
    """Fetch current weather or short-term forecast for a Vietnamese city.

    Use this only when the user asks about weather, road conditions, or
    whether it will rain on the travel route. `date` is optional (YYYY-MM-DD);
    if omitted, returns the current conditions. Forecast supports up to 5
    days ahead (OpenWeather free tier).

    Returns a short Vietnamese weather description, or a Vietnamese fallback
    message when the location is unknown or the API is unreachable.
    """
    loc = (location or "").strip()
    if not loc:
        return _WEATHER_NOT_FOUND_MSG.format(location=location)

    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return _WEATHER_TIMEOUT_MSG

    today_str = datetime.now(VN_TZ).strftime("%Y-%m-%d")
    use_forecast = bool(date) and date != today_str

    params = {"q": loc, "appid": api_key, "units": "metric", "lang": "vi"}
    url = OPENWEATHER_URL_FORECAST if use_forecast else OPENWEATHER_URL_CURRENT

    try:
        resp = requests.get(url, params=params, timeout=EXTERNAL_TIMEOUT_S)
    except (requests.Timeout, requests.ConnectionError, requests.RequestException):
        return _WEATHER_TIMEOUT_MSG

    if resp.status_code == 404:
        return _WEATHER_NOT_FOUND_MSG.format(location=loc)
    if resp.status_code != 200:
        return _WEATHER_TIMEOUT_MSG

    try:
        data = resp.json()
    except ValueError:
        return _WEATHER_TIMEOUT_MSG

    if not use_forecast:
        return _format_weather(loc, "hôm nay", data)

    slots = [s for s in data.get("list", []) if str(s.get("dt_txt", "")).startswith(date)]
    if not slots:
        return _WEATHER_NOT_FOUND_MSG.format(location=loc)

    def _distance_to_noon(slot: Dict[str, Any]) -> int:
        txt = str(slot.get("dt_txt", ""))
        try:
            hour = int(txt.split(" ")[1].split(":")[0])
        except (IndexError, ValueError):
            hour = 0
        return abs(hour - 12)

    best = min(slots, key=_distance_to_noon)
    return _format_weather(loc, date, best)


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Câu hỏi hoặc từ khoá cần tra cứu.")


@tool("web_search", args_schema=WebSearchInput)
def web_search(query: str) -> str:
    """Search the web via Tavily for information not contained in the local data.

    Use this only for auxiliary questions the other tools can't answer, e.g.
    "Quán ăn gần bến xe X", "Đèo Y hôm nay có cấm đường không?". Do NOT use
    this to look up bus schedules — always prefer `search_bus_schedules` for
    trips.

    Returns a short Vietnamese summary of results, or a Vietnamese fallback
    message when there are no results or the API is unreachable.
    """
    q = (query or "").strip()
    if not q:
        return _WEB_NO_RESULTS_MSG

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return _WEB_NETWORK_ERROR_MSG

    payload = {
        "api_key": api_key,
        "query": q,
        "max_results": 3,
        "search_depth": "basic",
        "include_answer": True,
    }

    try:
        resp = requests.post(TAVILY_URL, json=payload, timeout=EXTERNAL_TIMEOUT_S)
    except (requests.Timeout, requests.ConnectionError, requests.RequestException):
        return _WEB_NETWORK_ERROR_MSG

    if resp.status_code != 200:
        return _WEB_NETWORK_ERROR_MSG

    try:
        data = resp.json()
    except ValueError:
        return _WEB_NETWORK_ERROR_MSG

    answer = (data.get("answer") or "").strip()
    results = data.get("results") or []

    if answer:
        return answer

    if results:
        lines = []
        for r in results[:3]:
            title = (r.get("title") or "").strip()
            content = (r.get("content") or "").strip()
            if title or content:
                lines.append(f"- {title}: {content}")
        if lines:
            return "\n".join(lines)

    return _WEB_NO_RESULTS_MSG


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
