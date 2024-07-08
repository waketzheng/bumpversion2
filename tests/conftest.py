import logging


# https://github.com/cubed-dev/cubed/blob/3442c31fb806c7c6396f122f6eaf134efd499fcc/conftest.py
def pytest_sessionfinish():
    logging.raiseExceptions = False
