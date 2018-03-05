import inspect
import traceback
import sys
import os.path
import functools
import logging
from logging.config import dictConfig
import decimal
import json
import asyncio
import importlib.util

from sqlalchemy import create_engine, event
from sqlalchemy.exc import ProgrammingError, DisconnectionError

from raven import Client

import urllib3
import certifi
from jsonrpc import JSONRPCResponseManager
from jsonrpc.utils import DatetimeDecimalEncoder
from jsonrpc.exceptions import JSONRPCDispatchException

from aiohttp import web

from transer import db, config


class ExceptionBaseClass(Exception):
    logger = logging.getLogger('fallback')

    def __init__(self, m):
        self.logger.exception(m, exc_info=True)


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
    engine = create_engine(uri, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        connection_record.info['pid'] = os.getpid()

    @event.listens_for(engine, "checkout")
    def checkout(dbapi_connection, connection_record, connection_proxy):
        pid = os.getpid()
        if connection_record.info['pid'] != pid:
            connection_record.connection = connection_proxy.connection = None
            raise DisconnectionError(
                "Connection record belongs to pid %s, "
                "attempting to check out in pid %s" %
                (connection_record.info['pid'], pid)
            )

    db.sqla_session.configure(bind=engine)
    db.meta.bind = engine

    db.meta.create_all(checkfirst=True)

    return engine


def dump_db_ddl():
    def dump(sql, *multiparams, **params):
        print(sql.compile(dialect=engine.dialect))

    engine = create_engine('postgresql://', strategy='mock', executor=dump)
    db.meta.create_all(engine, checkfirst=False)


def init_logging():
    if config['sentry_dsn']:
        sentry_config = {
            'level': 'ERROR',
            'class': 'raven.handlers.logging.SentryHandler',
            'dsn': config['sentry_dsn'],
            'release': config['app_release'],
            'environment': config['sentry_environment']
        }
    else:
        sentry_config = {
            'level': 'ERROR',
            'class': 'logging.NullHandler',
        }

    logging_config = {
        'version': 1,
        'disable_existing_loggers': True,

        'formatters': {
            'console': {
                'format': '[%(asctime)s][%(levelname)s] %(name)s '
                          '%(filename)s:%(funcName)s:%(lineno)d | %(message)s',
                'datefmt': '%H:%M:%S',
            },
        },

        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'console'
            },
            'sentry': sentry_config,
        },

        # TODO fine tuning of handlers
        'loggers': {
            '': {
                'handlers': ['console', 'sentry'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'sqlalchemy': {
                'handlers': ['console', 'sentry'],
                'level': 'INFO',
                'propagate': False
            }
        }
    }

    logging.config.dictConfig(logging_config)


def handler_fabric(executor, dispatcher):
    async def submitter(request):
        body = await request.text()
        future = executor.submit(subprocess_wrapper, jsonrpc_handler, dispatcher, request.headers, body)
        return await asyncio.wrap_future(future)   # future.result() нельзя, тк. нужен (a)wait в asyncio loop
    return submitter


async def json_from_request(req, *_, loads=functools.partial(json.loads, parse_float=decimal.Decimal)):
    body = await req.text()
    return loads(body) if body else None


def endpoint_fabric(executor, func):
    async def submitter(request):
        try:
            sync_request = {}

            # here socket object in fact, cannot be pickled
            sync_request['match_info'] = request.match_info
            sync_request['json'] = await json_from_request(request)

            future = executor.submit(subprocess_wrapper, func, sync_request)
            return await asyncio.wrap_future(future)   # future.result() нельзя, тк. нужен (a)wait в asyncio loop
        except Exception as e:
            if config['sentry_dsn']:
                sentry_client = Client(
                    dsn=config['sentry_dsn'],
                    release=config['app_release'],
                    environment=config['sentry_environment']
                )
                sentry_client.captureException()
            else:
                # If you wish you may gather this output in main process via multiprocessing.log_to_stderr() logger
                # by default, futures.ProcessPoolExecutor()'s processes propagate error() messages to main one
                root_multiprocessing_logger = logging.getLogger()
                root_multiprocessing_logger.error(traceback.format_exc())
                raise e
    return submitter


def subprocess_wrapper(func, *args, **kwargs):
    # Sqlalchemy's Engine to multiprocessing augmenter moved to init_db()
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if config['sentry_dsn']:
            sentry_client = Client(
                dsn=config['sentry_dsn'],
                release=config['app_release'],
                environment=config['sentry_environment']
            )
            sentry_client.captureException()
        else:
            # If you wish you may gather this output in main process via multiprocessing.log_to_stderr() logger
            # by default, futures.ProcessPoolExecutor()'s processes propagate error() messages to main one
            root_multiprocessing_logger = logging.getLogger()
            root_multiprocessing_logger.error(traceback.format_exc())
            raise e


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


# inspired by https://gist.github.com/Horace89/88316fb7e518cc629ccb63abec540e48
def delayed_schedule(func, args=None, kwargs=None, interval=60, *, loop, executor):
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    async def periodic_func():
        while True:
            future = executor.submit(subprocess_wrapper, func, *args, **kwargs)
            await asyncio.wrap_future(future)
            await asyncio.sleep(interval, loop=loop)

    return loop.create_task(periodic_func())


def create_delayed_scheduler(loop=None, executor=None):
    if loop is not None and executor is not None:
        return functools.partial(delayed_schedule, loop=loop, executor=executor)
    return None


# All these tricks with magic numbers need to work around the limitations of 'multiprocessing'
# and corresponding 'concurrent.futures': it cannot pickle same function with different
# (e.g. changed by @decorator) signature. So I need to pass some kind of mark through all execution flow
# to ensure that it performed right.
# http://www.jsonrpc.org/specification#parameter_structures
def jsonrpc_caller(target_uri=None, catchables=()):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if len(args) > 0 and len(kwargs) > 0:
                raise JSONRPCDispatchException(-32600, 'Positional and named args cannot be mixed')

            if len(args) and args[-1] == 'a237e8d6-1af0-4c22-8d47-062bb6900b18':  # magic number :)
                args.pop()
                return func(*args, **kwargs)
            if kwargs.pop('__local_runnable__', None):
                return func(*args, **kwargs)

            if len(args) > 0:
                params = {}
                func_params = inspect.signature(func).parameters
                for i, p in enumerate(func_params):
                    params[p] = args[i]
            else:
                params = kwargs

            params['__local_runnable__'] = 'a237e8d6-1af0-4c22-8d47-062bb6900b18'  # magic number :)
            payload = {
                "method": func.__name__,
                "params": params,
                "jsonrpc": "2.0",
                "id": 0,
            }

            encoded_data = json.dumps(payload, cls=DatetimeDecimalEncoder).encode('utf-8')

            http = urllib3.PoolManager(
                ca_certs=certifi.where(),
                cert_reqs='CERT_REQUIRED'
            )
            resp = http.request(
                'POST',
                target_uri,
                body=encoded_data,
                headers={'Content-Type': 'application/json'},
                retries=3
            )

            decoded_resp = json.loads(resp.data)

            if decoded_resp.get('result', None):
                return decoded_resp['result']
            else:
                exceptions = {x.__name__: x for x in catchables}
                error_data = decoded_resp['error']['data']
                remote_exception_args = error_data['args']
                if error_data['type'] in exceptions:
                    remote_exception = exceptions[error_data['type']]
                    raise remote_exception(*remote_exception_args)
                else:
                    unknown_exception = Exception
                    raise unknown_exception(*remote_exception_args)

        return wrapper if target_uri is not None else func
    return decorator
