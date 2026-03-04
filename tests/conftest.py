"""Shared fixtures for traceback-ai tests."""



def make_exception_info(msg="test error", exc_class=ValueError):
    """Helper: create (exc_type, exc_value, exc_tb) for a real exception."""
    try:
        raise exc_class(msg)
    except exc_class:
        import sys

        return sys.exc_info()
