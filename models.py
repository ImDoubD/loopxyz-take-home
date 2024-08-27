from sqlalchemy import Column, Integer, String, DateTime, Float, PrimaryKeyConstraint
from database import Base

class StoreStatus(Base):
    __tablename__ = "store_status"

    store_id = Column(String, index=True)
    timestamp_utc = Column(DateTime(timezone=True))
    status = Column(String)

    __table_args__ = (PrimaryKeyConstraint('store_id', 'timestamp_utc'),)


class BusinessHours(Base):
    __tablename__ = "business_hours"

    store_id = Column(String, index=True)
    day = Column(Integer)
    start_time_local = Column(String)
    end_time_local = Column(String)

    __table_args__ = (PrimaryKeyConstraint('store_id', 'day', 'start_time_local'),)


class Timezone(Base):
    __tablename__ = "timezone"

    store_id = Column(String, unique=True, index=True)
    timezone_str = Column(String)

    __table_args__ = (PrimaryKeyConstraint('store_id'),)


class Report(Base):
    __tablename__ = "reports"

    report_id = Column(String, index=True)
    store_id = Column(String, index=True)
    uptime_last_hour = Column(Float)
    uptime_last_day = Column(Float)
    uptime_last_week = Column(Float)
    downtime_last_hour = Column(Float)
    downtime_last_day = Column(Float)
    downtime_last_week = Column(Float)

    __table_args__ = (PrimaryKeyConstraint('report_id', 'store_id'),)