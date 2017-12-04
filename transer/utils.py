import logging
import json
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError

from . import db


class ExceptionBaseClass(Exception):
    logger = logging.getLogger('fallback')

    def __init__(self, m):
        json_msg = {
            'subsystem': self.logger.name,
            'timestamp': datetime.utcnow().isoformat(),
            'exception': self.__class__.__mro__[0].__name__,
            'message': m
        }
        self.logger.warning(json.dumps(json_msg))


def recreate_entire_database(engine):
    connection = engine.connect()

    try:
        connection.execute('DROP SCHEMA BTC_PRIVATE CASCADE;')
    except ProgrammingError:
        pass
    connection.execute('CREATE SCHEMA BTC_PRIVATE;')

    try:
        connection.execute('DROP SCHEMA BTC_PUBLIC CASCADE;')
    except ProgrammingError:
        pass
    connection.execute('CREATE SCHEMA BTC_PUBLIC;')

    connection.close()


def init_db(uri):
    engine = create_engine(uri)
    db.sqla_session.configure(bind=engine)
    db.meta.bind = engine
    return engine


def init_logging(level=100):
    # default_formatter = '%(asctime)s %(levelname)-8s %(name)-16s %(message)s'
    default_formatter = '%(message)s'

    default_handler = logging.StreamHandler()
    default_formatter = logging.Formatter(default_formatter)
    default_handler.setFormatter(default_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(default_handler)
    root_logger.setLevel(level)
