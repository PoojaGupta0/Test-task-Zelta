from copy import deepcopy
import logging
import time
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from asyncio.exceptions import CancelledError
from utils.exceptions import PlaywrightInterceptError
from browser_surf import with_page


@with_page(headless=True)
def intercept_json_playwright(
    page_url: str,
    json_url_subpart: str,
    page: Page = None,
    json_detect_error: callable = None,
    json_parse_result: callable = None,
    captcha_solver_function: callable = None,
    max_refresh: int = 1,
    timeout: int = 4000,
    goto_timeout=30000,
    **kwargs,
) -> dict:
    """Intercept JSON data using Playwright, handle errors, and parse the result.

    Args:
        page_url (str): The URL of the web page.
        json_url_subpart (str): Subpart of the JSON URL to intercept.
        page (Page): Playwright Page object (optional).
        json_detect_error (callable): Function to detect and handle JSON errors (optional).
        json_parse_result (callable): Function to parse the JSON result (optional).
        captcha_solver_function (callable): Function to solve captchas (optional).
        max_refresh (int): Maximum number of page refresh attempts (default 1).
        timeout (int): Maximum time to wait for JSON data (default 4000 milliseconds).
        goto_timeout: Timeout for page navigation (default 30000 milliseconds).

    Returns:
        dict: The intercepted JSON data or an error message.
    """
    time_spent = 0
    nb_refresh = 0
    captcha_to_solve = False
    is_error = False
    target_json = {}

    def handle_response(response):
        if json_url_subpart in response.url:
            try:
                buffer = response.json()
            except Exception as jde:
                buffer = {"error": f"exception when trying to intercept:{str(jde)}"}

            if not "error" in buffer:
                target_json["data"] = buffer
            else:
                # Add coustom Exception
                target_json["data"] = PlaywrightInterceptError(
                    message=buffer["error"]
                ).get_response()

    page.on("response", handle_response)

    try:
        page.goto(page_url, timeout=goto_timeout)
    except:
        pass

    while (time_spent <= timeout) and (nb_refresh < max_refresh):
        s = time.perf_counter()
        target_json = target_json.get("data", {})
        logging.debug(
            f"time_spent : {time_spent}. target_json keys: {target_json.keys()}"
        )

        result = target_json
        is_error = False

        if not target_json:
            # Add coustom Exception
            result = PlaywrightInterceptError(
                message="An empty json was collected after calling the hidden API."
            ).get_response()
        elif result.get("error") == "CaptchaRaisedError":
            captcha_to_solve = True
        else:
            break

        if callable(json_detect_error):
            is_error, result = json_detect_error(result)

        if captcha_to_solve and callable(captcha_solver_function):
            ask_for_refresh, captcha_solved = captcha_solver_function(page)
            if captcha_solved:
                captcha_to_solve = False
                target_json = {}
                result = {}

            if ask_for_refresh:
                try:
                    logging.debug("refresh")
                    nb_refresh += 1
                    ask_for_refresh = False
                    page.goto(page_url, timeout=3000)
                except:
                    pass

        duration = time.perf_counter() - s
        if duration * 1000 < 500:
            remaining_sleep_time = 500 - int(duration * 1000)
            page.wait_for_timeout(remaining_sleep_time)

        duration = time.perf_counter() - s
        time_spent += duration * 1000
    if (not is_error) and callable(json_parse_result):
        result = json_parse_result(result)

    return result


@with_page(headless=True)
def intercept_json_playwright_old(
    page_url: str,
    json_url_subpart: str,
    page: Page = None,
    json_detect_error: callable = None,
    json_parse_result: callable = None,
    wait_seconds: int = 4,
    **kwargs,
) -> dict:
    """Intercept JSON data using Playwright (legacy method), handle errors, and parse the result.

    Args:
        page_url (str): The URL of the web page.
        json_url_subpart (str): Subpart of the JSON URL to intercept.
        page (Page): Playwright Page object (optional).
        json_detect_error (callable): Function to detect and handle JSON errors (optional).
        json_parse_result (callable): Function to parse the JSON result (optional).
        wait_seconds (int): Maximum wait time in seconds for JSON data (default 4 seconds).

    Returns:
        dict: The intercepted JSON data or an error message.
    """
    target_json = {}

    def handle_response(response):
        try:
            if json_url_subpart in response.url:
                try:
                    buffer = response.json()
                except Exception as jde:
                    buffer = {"error": f"exception when trying to intercept:{str(jde)}"}

                if not buffer.get("error"):
                    target_json["data"] = buffer
                else:
                    # Add coustom Exception
                    target_json["data"] = PlaywrightInterceptError(
                        message=buffer["error"]
                    ).get_response()
        except CancelledError:
            logging.debug("handle_response was correctly canceled")

    page.on("response", handle_response)

    try:
        page.goto(page_url)
    except PlaywrightTimeoutError as err:
        return {
            "error": "PlaywrightTimeoutError",
            "error_message": str(err),
            "data": {},
        }
    except Exception as err:
        return {"error": "PlaywrightGotoError", "error_message": str(err), "data": {}}

    for _ in range(wait_seconds * 2):
        page.wait_for_timeout(500)
        target_json = target_json.get("data", {})

        logging.debug(f"target_json keys: {target_json.keys()}")
        if not target_json:
            # Add coustom Exception
            result = PlaywrightInterceptError(
                message="An empty json was collected after calling the hidden API."
            ).get_response()
        else:
            result = {"error": None, "error_message": None, "data": target_json}
            break

    if json_detect_error:
        is_error, result = json_detect_error(result)

    if (not is_error) and json_parse_result:
        result = json_parse_result(result)

    return result


@with_page(headless=True)
def intercept_json_playwright_multiple(
    page_url: str,
    json_url_subpart: str,
    page=None,
    json_detect_error: callable = None,
    json_parse_result: callable = None,
    wait_seconds: int = 4,
    expect_more: int = 0,
    **kwargs,
) -> dict:
    """Intercept JSON data using Playwright, handle multiple responses, errors, and parse the result.

    Args:
        page_url (str): The URL of the web page.
        json_url_subpart (str): Subpart of the JSON URL to intercept.
        page (Page): Playwright Page object (optional).
        json_detect_error (callable): Function to detect and handle JSON errors (optional).
        json_parse_result (callable): Function to parse the JSON result (optional).
        wait_seconds (int): Maximum wait time in seconds for JSON data (default 4 seconds).
        expect_more (int): Number of additional expected responses (default 0).

    Returns:
        dict: The intercepted JSON data or an error message.
    """
    target_json = {}

    def handle_response(response):
        try:
            if json_url_subpart in response.url:
                try:
                    buffer = response.json()
                except Exception as jde:
                    buffer = {"error": f"exception when trying to intercept:{str(jde)}"}

                if not buffer.get("error"):
                    target_json["data"] = buffer
                else:
                    # Add coustom Exception
                    target_json["data"] = PlaywrightInterceptError(
                        message=buffer["error"]
                    ).get_response()
        except CancelledError:
            logging.debug("handle_response was correctly canceled")

    page.on("response", handle_response)

    try:
        page.goto(page_url)
    except PlaywrightTimeoutError as err:
        pass
    except Exception as err:
        return {"error": "PlaywrightGotoError", "error_message": str(err), "data": {}}

    is_error = True
    # Add coustom Exception
    result = PlaywrightInterceptError(
        message="An empty json was collected after calling the hidden API."
    ).get_response()

    for _ in range(wait_seconds * 2):
        page.wait_for_timeout(500)
        target_json = target_json.get("data", {})

        logging.debug(f"target_json keys: {target_json.keys()}")
        if target_json:
            result = target_json

            if json_detect_error:
                is_error, result = json_detect_error(result)

            if not is_error or expect_more == 0:
                break
            else:
                expect_more -= 1

    if (not is_error) and callable(json_parse_result):
        result = json_parse_result(result)

    return result


def request_json_playwright(
    json_url: str,
    json_detect_error: callable = None,
    json_parse_result: callable = None,
    **kwargs,
) -> dict:
    """Request JSON data using Playwright, handle errors, and parse the result.

    Args:
        json_url (str): The URL of the JSON data.
        json_detect_error (callable): Function to detect and handle JSON errors (optional).
        json_parse_result (callable): Function to parse the JSON result (optional).
        **kwargs: Additional keyword arguments to pass to `intercept_json_playwright`.

    Returns:
        dict: The intercepted JSON data or an error message.
    """
    result = intercept_json_playwright(
        page_url=json_url,
        json_url_subpart=json_url,
        json_detect_error=json_detect_error,
        json_parse_result=json_parse_result,
        **kwargs,
    )

    return result
