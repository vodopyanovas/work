
import re
from config import db_source_mssql, now, days_ago
# from config import db_source

from sqlalchemy import Column, Integer, String, Float, BigInteger, SmallInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


Base = declarative_base()
engine = create_engine(db_source_mssql, echo=False)
# engine = create_engine(db_source, echo=False)
Session = sessionmaker(bind=engine)
session = Session()


def create_db():
    Base.metadata.create_all(engine)


def drop_old_tables():
    tables = engine.table_names()
    del_tables = []

    pattern = re.compile(days_ago + '_' + r"\w+")

    for table in tables:
        search = re.search(pattern, table)
        if search:
            del_tables.append(search[0])

    for table in del_tables:
        command = "DROP TABLE [dbo].[{}]".format(table)
        session.execute(command)
        print(command)
    session.commit()


def drop_all():
    tables = engine.table_names()
    for table in tables:
        command = "DROP TABLE [dbo].[{}]".format(table)
        session.execute(command)
        print(command)
    session.commit()


class NewOrderSingle(Base):
    __tablename__ = now[:-2] + '_' + 'NewOrderSingle'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    server_id = Column(SmallInteger)
    timestamp = Column(String(35))
    sess_id = Column(String(20))
    tw_login = Column(String(30))
    msg_type = Column('type', String(30))

    security_id = Column('SecurityID', Integer)
    price = Column(Float)
    order_qty = Column('OrderQty', Integer)
    cl_ord_id = Column('ClOrdID', String(25))  # BigInteger
    cl_ord_link_ID = Column('ClOrdLinkID', BigInteger)  # BigInteger
    order_id = Column('OrderID', BigInteger)  # BigInteger
    moment = Column(String(30))
    side = Column(SmallInteger)
    check_limit = Column('CheckLimit', SmallInteger)
    account = Column(String(7))
    expire_date = Column('ExpireDate', String(30))
    time_in_force = Column('TimeInForce', SmallInteger)
    trading_sess_id = Column('TradingSessionID', Integer)
    ord_rej_reason = Column('OrdRejReason', SmallInteger)
    flags = Column('flags', String(20))


class OrderCancelRequest(Base):
    __tablename__ = now[:-2] + '_' + 'OrderCancelRequest'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    server_id = Column(SmallInteger)
    timestamp = Column(String(35))
    sess_id = Column(String(20))
    tw_login = Column(String(30))
    msg_type = Column('type', String(30))

    order_qty = Column('OrderQty', Integer)
    cl_ord_id = Column('ClOrdID', String(25))
    cl_ord_link_ID = Column('ClOrdLinkID', BigInteger)
    order_id = Column('OrderID', BigInteger)
    moment = Column(String(30))
    account = Column(String(7))
    trading_sess_id = Column('TradingSessionID', Integer)
    ord_rej_reason = Column('OrdRejReason', SmallInteger)
    flags = Column('Flags', String(20))


class ExecutionSingleReport(Base):
    __tablename__ = now[:-2] + '_' + 'ExecutionSingleReport'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    server_id = Column(SmallInteger)
    timestamp = Column(String(35))
    sess_id = Column(String(20))
    tw_login = Column(String(30))
    msg_type = Column('type', String(30))

    security_id = Column('SecurityID', Integer)
    cl_ord_id = Column('ClOrdID', String(25))
    cl_ord_link_ID = Column('ClOrdLinkID', BigInteger)
    order_id = Column('OrderID', BigInteger)
    trd_match_ID = Column('TrdMatchID', BigInteger)
    side = Column(SmallInteger)
    order_qty = Column('OrderQty', Integer)
    moment = Column(String(30))
    trading_sess_id = Column('TradingSessionID', Integer)
    flags = Column(String(20))
    last_px = Column('LastPx', Float)
    last_qty = Column('LastQty', Integer)


class NewOrderMultileg(Base):
    __tablename__ = now[:-2] + '_' + 'NewOrderMultileg'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    server_id = Column(SmallInteger)
    timestamp = Column(String(35))
    sess_id = Column(String(20))
    tw_login = Column(String(30))
    msg_type = Column('type', String(30))

    security_id = Column('SecurityID', Integer)
    price = Column(Float)
    order_qty = Column('OrderQty', Integer)
    cl_ord_id = Column('ClOrdID', String(25))
    cl_ord_link_ID = Column('ClOrdLinkID', BigInteger)
    order_id = Column('OrderID', BigInteger)
    moment = Column(String(30))
    side = Column(SmallInteger)
    account = Column(String(7))
    expire_date = Column('ExpireDate', String(30))
    time_in_force = Column('TimeInForce', SmallInteger)
    trading_sess_id = Column('TradingSessionID', Integer)
    ord_rej_reason = Column('OrdRejReason', SmallInteger)
    flags = Column(String(20))


class OrderMassCancelRequest(Base):
    __tablename__ = now[:-2] + '_' + 'OrderMassCancelRequest'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    server_id = Column(SmallInteger)
    timestamp = Column(String(35))
    sess_id = Column(String(20))
    tw_login = Column(String(30))
    msg_type = Column('type', String(30))

    order_qty = Column('OrderQty', Integer)
    cl_ord_id = Column('ClOrdID', String(25))
    cl_ord_link_ID = Column('ClOrdLinkID', BigInteger)
    security_id = Column('SecurityID', Integer)
    security_type = Column('SecurityType', SmallInteger)
    security_group = Column('SecurityGroup', String(25))
    side = Column(SmallInteger)
    moment = Column(String(30))
    account = Column(String(7))
    trading_sess_id = Column('TradingSessionID', Integer)
    ord_rej_reason = Column('OrdRejReason', SmallInteger)
    flags = Column('Flags', String(20))
    total_affected_orders = Column('TotalAffectedOrders', Integer)


class ExecutionMultilegReport(Base):
    __tablename__ = now[:-2] + '_' + 'ExecutionMultilegReport'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    server_id = Column(SmallInteger)
    timestamp = Column(String(35))
    sess_id = Column(String(20))
    tw_login = Column(String(30))
    msg_type = Column('type', String(30))

    security_id = Column('SecurityID', Integer)
    cl_ord_id = Column('ClOrdID', String(25))
    cl_ord_link_ID = Column('ClOrdLinkID', BigInteger)
    order_id = Column('OrderID', BigInteger)
    trd_match_ID = Column('TrdMatchID', BigInteger)
    side = Column(SmallInteger)
    order_qty = Column('OrderQty', Integer)
    moment = Column(String(30))
    trading_sess_id = Column('TradingSessionID', Integer)
    flags = Column(String(20))
    last_px = Column('LastPx', Float)
    last_qty = Column('LastQty', Integer)
    leg_price = Column('LegPrice', Float)


class OrderReplaceRequest(Base):
    __tablename__ = now[:-2] + '_' + 'OrderReplaceRequest'

    _id = Column('id', Integer, primary_key=True, autoincrement=True)
    server_id = Column(SmallInteger)
    timestamp = Column(String(35))
    sess_id = Column(String(20))
    tw_login = Column(String(30))
    msg_type = Column('type', String(30))

    price = Column(Float)
    order_qty = Column('OrderQty', Integer)
    cl_ord_id = Column('ClOrdID', String(25))
    cl_ord_link_ID = Column('ClOrdLinkID', BigInteger)
    order_id = Column('OrderID', BigInteger)
    prev_order_id = Column('PrevOrderID', BigInteger)
    moment = Column(String(30))
    account = Column(String(7))
    trading_sess_id = Column('TradingSessionID', Integer)
    ord_rej_reason = Column('OrdRejReason', SmallInteger)
    flags = Column(String(20))
    mode = Column(SmallInteger)
    check_limit = Column('CheckLimit', SmallInteger)
    trd_match_ID = Column('TrdMatchID', BigInteger)
