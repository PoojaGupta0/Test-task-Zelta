import unittest
from unittest.mock import MagicMock
from web_intercept import (
    intercept_json_playwright,
    request_json_playwright,
    intercept_json_playwright_multiple,
)


class BaseJsonTest(unittest.TestCase):
    def json_detect_error(self, result):
        if result.get("error"):
            return True, result
        else:
            return False, result

    def json_parse_result(self, result):
        return {"success": True, "data": result}


class TestRequestJsonPlaywright(BaseJsonTest):
    def test_request_json_playwright_success(self):
        # Mock the Page object
        mock_page = MagicMock()
        intercepted_json_response = request_json_playwright(
            json_url="https://www.boredapi.com/api/activity",
            timeout=5000,
            page=mock_page,
            json_detect_error=self.json_detect_error,
            json_parse_result=self.json_parse_result,
        )
        self.assertEqual(intercepted_json_response.get("success"), True)

    def test_request_json_playwright_error(self):
        # Mock the Page object
        mock_page = MagicMock()
        intercepted_json_response = intercept_json_playwright(
            page_url="https://invalid.url",
            json_url_subpart="/nonexistent",
            page=mock_page,
            json_detect_error=self.json_detect_error,
            json_parse_result=self.json_parse_result,
        )

        # Perform assertions
        self.assertEqual(
            intercepted_json_response.get("error"), "PlaywrightInterceptError"
        )


class TestInterceptJsonPlaywrightMultiple(BaseJsonTest):
    def test_intercept_json_playwright_multiple_success(self):
        # Mock the Page object
        mock_page = MagicMock()

        # Call the function under test
        intercepted_json_response = intercept_json_playwright_multiple(
            page_url="https://www.boredapi.com/api/activity",
            json_url_subpart="/api/activity",
            page=mock_page,
            json_detect_error=self.json_detect_error,
            json_parse_result=self.json_parse_result,
        )

        # Perform assertions for success scenario
        self.assertIsNotNone(intercepted_json_response)
        self.assertIsNone(intercepted_json_response.get("error"))


if __name__ == "__main__":
    unittest.main()
