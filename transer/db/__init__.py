from sqlalchemy import Column, Integer, Sequence
from sqlalchemy.schema import MetaData
from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker


class IdMixin(object):
    @declared_attr
    def id(self):
        tablename = getattr(self, '__tablename__')  # No defaults. AttributeError expected in 'bare' case
        col_name = 'id'
        return Column(col_name, Integer, Sequence(tablename + col_name), primary_key=True)


class CustomBase(IdMixin):
    pass


sqla_session = scoped_session(sessionmaker(autocommit=False, autoflush=True))
meta = MetaData()

Base = declarative_base(cls=CustomBase, metadata=meta)
Base.query = sqla_session.query_property()
