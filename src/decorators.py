import locale
from functools import wraps
from typing import Callable, Any


def set_locale_decorator[RT, **P](func: Callable[P, RT]) -> Callable[P, RT]:
    """Temp added ru local for correct parsing date-times"""

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> RT:
        old_locale = locale.getlocale()
        try:
            locale.setlocale(locale.LC_ALL, "ru_RU.UTF-8")
            result = func(*args, **kwargs)
        finally:
            locale.setlocale(locale.LC_ALL, old_locale)

        return result

    return wrapper


def decohints(decorator: Callable[..., Any]) -> Callable[..., Any]:
    """
    Small helper which helps to say IDE: "decorated method has the same params and return types"
    """
    return decorator
