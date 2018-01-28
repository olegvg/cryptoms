import logging
import json
import asyncio
import importlib.util
import sys
import os.path
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.exc import ProgrammingError

from jsonrpc import JSONRPCResponseManager
from jsonrpc.utils import DatetimeDecimalEncoder
from aiohttp import web

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

    try:
        connection.execute('DROP SCHEMA ETH_PRIVATE CASCADE;')
    except ProgrammingError:
        pass
    connection.execute('CREATE SCHEMA ETH_PRIVATE;')

    try:
        connection.execute('DROP SCHEMA ETH_PUBLIC CASCADE;')
    except ProgrammingError:
        pass
    connection.execute('CREATE SCHEMA ETH_PUBLIC;')

    try:
        connection.execute('DROP SCHEMA COMMON_PUBLIC CASCADE;')
    except ProgrammingError:
        pass
    connection.execute('CREATE SCHEMA COMMON_PUBLIC;')

    connection.close()


def init_db(uri):
    engine = create_engine(uri)
    db.sqla_session.configure(bind=engine)
    db.meta.bind = engine

    db.meta.create_all(checkfirst=True)

    return engine


def dump_db_ddl():
    def dump(sql, *multiparams, **params):
        print(sql.compile(dialect=engine.dialect))

    engine = create_engine('postgresql://', strategy='mock', executor=dump)
    db.meta.create_all(engine, checkfirst=False)


def init_logging(level=100):
    # default_formatter = '%(asctime)s %(levelname)-8s %(name)-16s %(message)s'
    default_formatter = '%(message)s'

    default_handler = logging.StreamHandler()
    default_formatter = logging.Formatter(default_formatter)
    default_handler.setFormatter(default_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(default_handler)
    root_logger.setLevel(level)


def jsonrpc_handler(dispatcher, headers, body):
    if headers.get('Content-Type') != 'application/json':
        error_response = {
            'error': {
                'code': -32700,
                'message': 'Parse error'
            },
            'id': None,
            'jsonrpc': '2.0'
        }
        return web.Response(text=json.dumps(error_response), headers={'Content-Type': 'application/json'})

    response = JSONRPCResponseManager.handle(body, dispatcher)
    response.serialize = lambda s: json.dumps(s, cls=DatetimeDecimalEncoder)
    return web.Response(text=response.json, headers={'Content-Type': 'application/json'})


def concurrent_fabric(executor):
    def json_rpc_handler_fabric(dispatcher):
        async def submitter(request):
            body = await request.text()
            future = executor.submit(jsonrpc_handler, dispatcher, request.headers, body)
            return await asyncio.wrap_future(future)   # future.result() нельзя, тк. нужен (a)wait в asyncio loop
        return submitter
    return json_rpc_handler_fabric


def bulk_importer(path):
    _, package_name = os.path.split(path)

    only_py_files = [f for f in os.listdir(path)
                     if os.path.isfile(os.path.join(path, f)) and not f.startswith('__')]

    py_files = [os.path.join(path, f) for f in only_py_files]

    # Можно было бы не заморачиваться использовать UUID4 в качестве имени модуля,
    # но тогда бы traceback был неинформативный
    module_names = [package_name + '.' + p.split('.')[0] for p in only_py_files]

    module_specs = dict(zip(module_names, py_files))

    for m, f in module_specs.items():
        spec = importlib.util.spec_from_file_location(m, f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[m] = mod  # Без этого pickle в json-rpc работать не будет. Да и вообще...


def docstrings_from_dispatcher(dispatcher):
    json_rpc_methods = dispatcher.method_map

    methods = {k: v.__doc__ for k, v in json_rpc_methods.items()}

    return methods
