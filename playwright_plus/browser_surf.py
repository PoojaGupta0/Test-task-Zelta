# Built-in imports
import logging
from random import randint

# Public 3rd party packages imports
from playwright.sync_api import sync_playwright
from playwright.sync_api._generated import Page, Locator
from asyncio.exceptions import CancelledError

# Private packages imports
# Local functions and relative imports
# Constants imports
# New constants
EXCLUDED_RESOURCES_TYPES = ["stylesheet", "image", "font", "svg"]

__all__ = [
    "check_for_loaded_marker",
    "open_new_page",
    "wait_after_execution",
    "with_page",
]


def create_block_resources(resources_to_block: list):
    """Create a resource blocking function based on a list of resource types.

    Args:
        resources_to_block (list): List of resource types to block.

    Returns:
        callable: A route handling function that blocks specified resource types and allows others to continue.
    """

    def _block_resources(route):
        try:
            if route.request.resource_type in resources_to_block:
                route.abort()

            else:
                route.continue_()

        except CancelledError as err:
            logging.debug("block_resources was correctly canceled")

    return _block_resources


### WEB BROWSER AND PAGE OPENING


def _instantiate_browser_context_page(
    p,
    proxy_info: dict = None,
    headless: bool = True,
    accept_downloads: bool = True,
    block_resources: bool | list = True,
    cookies: list[dict] = None,
    browser_type: str = "chromium",
    **kwargs,
):
    """Instantiate a browser, browser context, and web page for automated web interactions.

    Args:
        p: Playwright instance.
        proxy_info (dict, optional): Proxy information (e.g., {"server": "http://proxyserver:port"}).
        headless (bool, optional): Whether to run the browser in headless mode (default True).
        accept_downloads (bool, optional): Whether to accept downloads (default True).
        block_resources (bool | list, optional): Whether to block specific resource types or a list of resource types to block (default True).
        cookies (list[dict], optional): List of cookies to set in the browser context (default None).
        browser_type (str, optional): Type of browser to launch ("chromium" or "firefox", default "chromium").

    Returns:
        tuple: A tuple containing the browser instance, browser context, and web page.

    Note:
        This function sets up a browser with specific configurations and can block resources as specified. It is intended for automated web interactions.
    """
    logging.debug(
        f"[playwright_plus] open a browser : headless={headless}, proxy_info={proxy_info.get('server') if isinstance(proxy_info, dict) else None}"
    )
    match browser_type:
        case "chromium":
            browser = p.chromium.launch(headless=headless, proxy=proxy_info)
        case "firefox":
            browser = p.firefox.launch(headless=headless, proxy=proxy_info)
    # create the browser context
    logging.debug(
        f"[playwright_plus] open a browser context: accept_downloads={accept_downloads}, with {len(cookies) if cookies else 0} cookies set(s)"
    )
    context = browser.new_context(accept_downloads=accept_downloads)
    context.add_init_script(
        """
            navigator.webdriver = false
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            })
        """
    )
    if cookies:
        context.add_cookies(cookies)

    # open a web page
    logging.debug(
        f"[playwright_plus] open a new page: blocked resources={EXCLUDED_RESOURCES_TYPES if block_resources==True else block_resources}"
    )
    page = context.new_page()
    if block_resources:
        resources_to_block = (
            EXCLUDED_RESOURCES_TYPES if block_resources == True else block_resources
        )

        def _block_resources(route):
            try:
                if route.request.resource_type in resources_to_block:
                    route.abort()

                else:
                    route.continue_()

            except CancelledError as err:
                logging.debug("block_resources was correctly canceled")

        page.route("**/*", _block_resources)

    return browser, context, page


def open_new_page(
    proxy_info: dict = None,
    headless: bool = True,
    accept_downloads: bool = True,
    block_resources: bool | list = True,
    cookies: list[dict] = None,
    **kwargs,
):
    """Open a new browser page for automated web interactions with customizable settings.

    Args:
        proxy_info (dict, optional): Proxy information (e.g., {"server": "http://proxyserver:port"}).
        headless (bool, optional): Whether to run the browser in headless mode (default True).
        accept_downloads (bool, optional): Whether to accept downloads (default True).
        block_resources (bool | list, optional): Whether to block specific resource types or a list of resource types to block (default True).
        cookies (list[dict], optional): List of cookies to set in the browser context (default None).
        **kwargs: Additional keyword arguments.

    Returns:
        tuple: A tuple containing the browser instance, browser context, and web page.

    Note:
        This function starts a new browser instance, sets up a browser context with specified configurations, and opens a new web page. It is designed for automated web interactions with customizable settings.
    """
    p = sync_playwright().start()

    browser, context, page = _instantiate_browser_context_page(
        p,
        proxy_info=proxy_info,
        headless=headless,
        accept_downloads=accept_downloads,
        block_resources=block_resources,
        cookies=cookies,
    )

    return browser, context, page


def with_page(**kwargs):
    """Decorator for automating web interactions with customizable browser settings.

    Args:
        **kwargs: Keyword arguments for customizing browser behavior.

    Returns:
        callable: A decorator function that wraps another function for web automation.

    Note:
        This decorator allows you to specify various browser settings such as accepting downloads, running in headless mode, blocking resources, using a proxy, and setting cookies. The wrapped function can access a preconfigured web page for web automation.
    """

    def decorator(func):
        def func_wrapper(*func_args, **func_kwargs):
            # by default, accept_downloads=True, headless=True, block_resources=True, no proxy, no cookies
            default = {
                "accept_downloads": True,
                "headless": True,
                "block_resources": True,
                "proxy_info": None,
            }
            for k, v in default.items():
                if k not in kwargs:
                    kwargs[k] = v

            # overwrite the decorator kwargs if the ones specified by the wrapped function
            kwargs.update(func_kwargs)

            # open browser, context and page with the conditions specified in the kwargs dictionary
            with sync_playwright() as p:
                browser, context, page = _instantiate_browser_context_page(p, **kwargs)

                # add the new page to the wrapped function kwargs
                func_kwargs["page"] = page

                # execute the function with the open page
                output = func(*func_args, **func_kwargs)

                # close the page and browser
                page.close()
                browser.close()

            return output

        return func_wrapper

    return decorator


### WEB SURFING
def _get_page_arg(func_args: list, func_kwargs: dict, func_name: str) -> Page:
    """Retrieve a Playwright Page object from function arguments or keyword arguments.

    Args:
        func_args (list): List of function arguments.
        func_kwargs (dict): Dictionary of function keyword arguments.
        func_name (str): The name of the decorated function.

    Returns:
        Page: A Playwright Page object.

    Raises:
        Exception: If the Page object is not found in function arguments or keyword arguments.

    Note:
        This function is used by decorators to retrieve a Page object from function arguments or keyword arguments.
    """
    page = None
    if func_kwargs:
        page = func_kwargs.get("page")
    if (not page) and func_args:
        page = func_args[0]
    if not isinstance(page, Page):
        raise Exception(
            f"One of the decorator expects the function `{func_name}` to have a page as first arg or as kwarg."
        )
    return page


def wait_after_execution(wait_ms: int = 2000, randomized: bool = True):
    """Decorator for adding a waiting period after executing a function on a web page.

    Args:
        wait_ms (int, optional): Time in milliseconds to wait after executing the function (default 2000 ms).
        randomized (bool, optional): Whether to randomize the waiting time within a range (default True).

    Returns:
        callable: A decorator function that wraps another function and adds a waiting period.

    Note:
        This decorator allows you to introduce a delay after executing a function on a web page. You can specify the waiting time in milliseconds, and if randomized is True, the actual waiting time will be randomized within a range.
    """

    def decorator(func):
        def func_wrapper(*func_args, **func_kwargs):
            # get the page object. Check the kwargs first, then the first args
            page = _get_page_arg(func_args, func_kwargs, func.__name__)

            # execute the function
            output = func(*func_args, **func_kwargs)

            # wait for the given time before moving to the next command
            nonlocal wait_ms
            # the wait_ms value can be overwritten if it is specified as a kwarg in the wrapped function
            if func_kwargs and ("wait_ms" in func_kwargs):
                wait_ms = func_kwargs.get("wait_ms")

            if randomized:
                # take a random number in the 15% range around the input time in millisecond
                min = int(wait_ms * 0.85 + 0.5)
                max = int(wait_ms * 1.15 + 0.5)
                wait_ms = randint(min, max)
            # wait for the given time before moving to the next command
            page.wait_for_timeout(wait_ms)

            return output

        return func_wrapper

    return decorator


def check_for_loaded_marker(
    marker: str | Locator = None,
    marker_strict: bool = False,
    load_message: str = None,
    timeout: int = 10000,
):
    """Decorator for checking the presence of a loaded marker on a web page.

    Args:
        marker (str | Locator, optional): The marker to check, either as a string selector or a Playwright Locator (default None).
        marker_strict (bool, optional): Whether to use strict marker selection (default False).
        load_message (str, optional): Custom message to log when the marker is loaded (default None).
        timeout (int, optional): Maximum time to wait for the marker to appear (default 10000 ms).

    Returns:
        callable: A decorator function that wraps another function and checks for a loaded marker.

    Note:
        This decorator allows you to check for the presence of a loaded marker on a web page. You can specify the marker as a string selector or a Playwright Locator. It provides flexibility in selecting markers and logging custom messages upon detection.
    """

    def decorator(func):
        def func_wrapper(*func_args, **func_kwargs):
            # get the page object. Check the kwargs first, then the first args
            page = _get_page_arg(func_args, func_kwargs, func.__name__)

            # execute the function
            output = func(*func_args, **func_kwargs)

            # build the marker locator if needed
            nonlocal marker
            if isinstance(marker, str):
                # add a dot before the marker if it misses it
                if not (marker_strict) and not (marker.startswith(".")):
                    marker = "." + marker
                # make the marker a playwright Locator
                marker = page.locator(marker)
                # wait for the marker to be visible
                marker.wait_for(timeout=timeout)
                logging.debug(
                    load_message
                    if load_message
                    else "[playwright_plus] loaded marker visible."
                )

            return output

        return func_wrapper

    return decorator
