from sqlalchemy import Column, Integer, Sequence
from sqlalchemy.schema import MetaData
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker


class IdMixin(object):
    @declared_attr
    def id(self):
        tablename = getattr(self, '__tablename__')  # No defaults. AttributeError expected in 'bare' case
        table_args = getattr(self, '__table_args__')

        # see http://docs.sqlalchemy.org/en/latest/orm/extensions/declarative/table_config.html#declarative-table-args
        if isinstance(table_args, dict):
            schema = table_args['schema']
        elif isinstance(table_args, tuple):
            schema = table_args[-1]['schema']
        else:
            schema = ''

        col_name = id.__name__
        return Column(col_name, Integer, Sequence(f'{tablename}_{col_name}', schema=schema), primary_key=True)


class CustomBase(IdMixin):
    pass


sqla_session = scoped_session(sessionmaker(autocommit=False, autoflush=True))
meta = MetaData()

Base = declarative_base(cls=CustomBase, metadata=meta)
Base.query = sqla_session.query_property()
