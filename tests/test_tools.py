import unittest
import json
import sys
import os
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import cả code mới của nhóm và class cũ
from src.tools.bus_tools import (
    search_bus_schedules,
    get_bus_operator_info,
    get_current_datetime,
    get_route_weather,
    web_search,
    BusBookingTools
)

class TestNewAgentTools(unittest.TestCase):
    """
    Bộ 20 Test Cases tiêu chuẩn (TDD) dùng kiểm thử toàn diện
    Các Tool mới mà team (nhánh Phong) vừa merge vào.
    """
    
    def setUp(self):
        self.old_tools = BusBookingTools()

    # ==========================================
    # TESTS CHO: search_bus_schedules (8 Cases)
    # ==========================================
    def test_01_search_valid_basic(self):
        """1. Tìm chuyến hợp lệ chỉ với Điểm đi/đến"""
        res = search_bus_schedules("Hà Nội", "Sa Pa")
        self._verify_json_list(res)

    def test_02_search_case_insensitive(self):
        """2. Tìm chuyến bất chấp Hoa/Thường"""
        res1 = search_bus_schedules("hà nội", "sa pa")
        res2 = search_bus_schedules("HÀ NỘI", "SA PA")
        self.assertEqual(res1, res2, "Lỗi: Không xử lý tốt chữ Hoa/Thường")
        self._verify_json_list(res1)

    def test_03_search_invalid_route(self):
        """3. Tìm tuyến đường không tồn tại"""
        res = search_bus_schedules("Hà Nội", "Cà Mau")
        self.assertIn("Không tìm thấy", res)

    def test_04_search_missing_inputs(self):
        """4. Cố tình bỏ trống điểm đi/đến"""
        res = search_bus_schedules("", "Sa Pa")
        self.assertIn("Lỗi: Thiếu điểm đi", res)

    def test_05_search_max_price_filter(self):
        """5. Lọc theo mức giá tối đa"""
        res = search_bus_schedules("Hà Nội", "Sa Pa", max_price=500000)
        lst = self._verify_json_list(res)
        for r in lst:
            self.assertLessEqual(r.get("price", 0), 500000)

    def test_06_search_vehicle_type(self):
        """6. Lọc theo loại xe"""
        res = search_bus_schedules("Sài Gòn", "Đà Lạt", vehicle_type="Limousine")
        lst = self._verify_json_list(res)
        for r in lst:
            self.assertIn("limousine", str(r.get("vehicle_type", "")).lower())

    def test_07_search_min_seats(self):
        """7. Lọc theo số ghế tối thiểu"""
        res = search_bus_schedules("Đà Nẵng", "Huế", min_available_seats=15)
        lst = self._verify_json_list(res)
        for r in lst:
            self.assertGreaterEqual(r.get("available_seats", 0), 15)

    def test_08_search_date_filter(self):
        """8. Lọc theo Ngày khởi hành"""
        res = search_bus_schedules("Hà Nội", "Sa Pa", departure_date="2024-05-10")
        if "Không tìm thấy" not in res:
            lst = self._verify_json_list(res)
            for r in lst:
                self.assertTrue(str(r.get("departure_time", "")).startswith("2024-05-10"))

    # ==========================================
    # TESTS CHO: get_bus_operator_info (3 Cases)
    # ==========================================
    def test_09_operator_info_valid(self):
        """9. Truy vấn thông tin nhà xe đúng ID"""
        res = get_bus_operator_info("COM-101")
        data = self._verify_dict(res)
        self.assertEqual(data.get("company_id"), "COM-101")

    def test_10_operator_info_invalid(self):
        """10. Truy vấn sai ID nhà xe"""
        res = get_bus_operator_info("COM-999")
        self.assertIn("Lỗi: Mã nhà xe", res)

    def test_11_operator_info_empty(self):
        """11. Truy vấn nhà xe rỗng"""
        res = get_bus_operator_info("")
        self.assertIn("Lỗi: Mã nhà xe", res)

    # ==========================================
    # TESTS CHO: get_current_datetime (1 Case)
    # ==========================================
    def test_12_get_datetime(self):
        """12. Lấy giờ hệ thống đúng format YYYY-MM-DD HH:MM:SS"""
        res = get_current_datetime()
        pattern = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"
        self.assertRegex(res, pattern)

    # ==========================================
    # TESTS CHO: get_route_weather (4 Cases)
    # ==========================================
    def test_13_weather_valid_location(self):
        """13. Hỏi thời tiết thành phố có thật"""
        res = get_route_weather("Hà Nội")
        self.assertIsInstance(res, str)

    def test_14_weather_empty_location(self):
        """14. Hỏi thời tiết rỗng"""
        res = get_route_weather("")
        self.assertIn("Lỗi: Không tìm thấy", res)

    def test_15_weather_with_date(self):
        """15. Hỏi thời tiết kèm ngày"""
        res = get_route_weather("Đà Nẵng", "2099-01-01") 
        # API free có thể giới hạn 5 ngày nên có thể ko thấy
        self.assertTrue("Lỗi" in res or "không tìm thấy" in res.lower() or "độ" in res.lower())

    def test_16_weather_timeout_mock(self):
        """16. Test thời tiết khi không cắm API Key (giả lập offline)"""
        old_env = os.environ.get("OPENWEATHER_API_KEY")
        os.environ["OPENWEATHER_API_KEY"] = ""
        res = get_route_weather("Hà Nội")
        self.assertIn("gián đoạn", res)
        if old_env is not None:
            os.environ["OPENWEATHER_API_KEY"] = old_env

    # ==========================================
    # TESTS CHO: web_search (2 Cases)
    # ==========================================
    def test_17_web_search_empty(self):
        """17. Tra cứu rỗng trên Web"""
        res = web_search("")
        self.assertIn("Không tìm thấy", res)

    def test_18_web_search_no_api_key(self):
        """18. Tra cứu khi ko cấu hình API Key (giả lập)"""
        old_env = os.environ.get("TAVILY_API_KEY")
        os.environ["TAVILY_API_KEY"] = ""
        res = web_search("Đèo Hải Vân")
        self.assertIn("Lỗi kết nối", res)
        if old_env is not None:
            os.environ["TAVILY_API_KEY"] = old_env

    # ==========================================
    # TESTS BẮT LỖI TEAM CODE BỎ QUÊN HÀM (2 Cases)
    # ==========================================
    def test_19_check_availability_unfinished(self):
        """19. Test hàm check_availability CŨ vẫn bị lờ đi TODO"""
        res = self.old_tools.check_availability("VN-009")
        self.assertNotIn("TODO", res, "Team Code đã quên migrate hàm check_availability sang dạng Tool!")

    def test_20_book_ticket_unfinished(self):
        """20. Test hàm book_ticket CŨ vẫn bị lờ đi TODO"""
        res = self.old_tools.book_ticket("VN-009", "Nguyễn Văn B", 1)
        self.assertNotIn("TODO", res, "Team Code đã quên migrate hàm book_ticket sang dạng Tool!")

    # ==========================================
    # HELPER METHOS
    # ==========================================
    def _verify_json_list(self, result):
        try:
            data = json.loads(result)
            self.assertIsInstance(data, list, "Kết quả trả về không phải mảng JSON (List)")
            return data
        except json.JSONDecodeError:
            self.fail(f"BUG: Output không phải JSON hợp lệ: {result}")

    def _verify_dict(self, result):
        try:
            data = json.loads(result)
            self.assertIsInstance(data, dict, "Kết quả trả về không phải dạng Object JSON (Dict)")
            return data
        except json.JSONDecodeError:
            self.fail(f"BUG: Output không phải JSON hợp lệ: {result}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
