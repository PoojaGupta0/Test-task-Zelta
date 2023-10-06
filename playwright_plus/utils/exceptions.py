from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError


def catch_TimeoutError(
    exception_class: Exception = Exception,
    message: str = None,
):
    def decorator(func):
        def func_wrapper(*args, **kwargs):
            try:
                output = func(*args, **kwargs)
                return output

            except PlaywrightTimeoutError as te:
                # instantiate the exception to raise.
                exception = exception_class(message)
                # customize the error message
                exception.message = f"[{func.__name__}] {exception.message}:\n{str(te)}"
                # raise the exception
                raise exception

        return func_wrapper

    return decorator


class PlaywrightPlusException(Exception):
    status_code = 500
    error_code = 99999
    error = "InternalServerError"
    error_message = "Internal Server Error"

    def __init__(self, message="Internal Server Error"):
        self.error_message = message
        super().__init__(self.error_message)

    def get_error_message(self):
        return self.error_message

    def get_response(self):
        return {
            "error": self.error,
            "error_code": str(self.error_code),
            "error_message": self.get_error_message(),
        }


class PlaywrightInterceptError(PlaywrightPlusException):
    error_code = 1
    status_code = 400
    error = "PlaywrightInterceptError"
    error_message = "Internal Server Error"


class PlaywrightInterceptJsonError(PlaywrightPlusException):
    error_code = 2
    status_code = 400
    error = "PlaywrightInterceptError"
    error_message = "An empty json was collected after calling the hidden API."
