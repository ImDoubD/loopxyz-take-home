from models import StoreStatus, BusinessHours, Timezone
import pytz
from datetime import datetime, timedelta
from sqlalchemy import select

async def calculate_uptime_downtime(store_id, db):
    # Fetch timezone information
    timezone_query = select(Timezone).filter(Timezone.store_id == store_id)
    timezone_result = await db.execute(timezone_query)
    timezone_query = timezone_result.scalar_one_or_none()
    if not timezone_query:
        return None  # Store not found
    timezone_str = timezone_query.timezone_str
    local_tz = pytz.timezone(timezone_str)

    # Fetch business hours
    business_hours = {}
    business_hours_query = select(BusinessHours).filter(BusinessHours.store_id == store_id)
    business_hours_result = await db.execute(business_hours_query)
    business_hours_query = business_hours_result.scalars().all()
    for bh in business_hours_query:
        if bh.day not in business_hours:
            business_hours[bh.day] = []
        business_hours[bh.day].append((bh.start_time_local, bh.end_time_local))

    # Set the reference date to January 25, 2023, 19:30 local time
    now = datetime(2023, 1, 25, 19, 30, tzinfo=local_tz)
    week_ago = now - timedelta(days=7)

    # Fetch store status entries
    status_query = select(StoreStatus).filter(
        StoreStatus.store_id == store_id,
        StoreStatus.timestamp_utc >= week_ago,
        StoreStatus.timestamp_utc <= now
    ).order_by(StoreStatus.timestamp_utc)
    status_result = await db.execute(status_query)
    status_entries = status_result.scalars().all()

    # Initialize counters
    uptime_last_hour = downtime_last_hour = 0
    uptime_last_day = downtime_last_day = 0
    uptime_last_week = downtime_last_week = 0

    def is_business_hour(timestamp):
        day_of_week = timestamp.weekday()
        return any(
            datetime.strptime(start_time, "%H:%M:%S").time() <= timestamp.time() <= datetime.strptime(end_time, "%H:%M:%S").time()
            for start_time, end_time in business_hours.get(day_of_week, [])
        )

    def calculate_business_hours(start, end):
        duration = timedelta()
        current = start
        while current < end:
            if is_business_hour(current):
                duration += min(timedelta(hours=1), end - current)
            current += timedelta(hours=1)
        return duration

    # Calculate uptime and downtime
    last_status = 'active'
    last_timestamp = week_ago

    for entry in status_entries:
        current_timestamp = entry.timestamp_utc.astimezone(local_tz)
        
        if is_business_hour(current_timestamp):
            time_diff = calculate_business_hours(last_timestamp, current_timestamp)
            
            if last_status == 'active':
                uptime_last_week += time_diff.total_seconds() / 3600
                if (now - current_timestamp).days < 1:
                    uptime_last_day += time_diff.total_seconds() / 3600
                if (now - current_timestamp).total_seconds() <= 3600:
                    uptime_last_hour += min(time_diff.total_seconds() / 60, 60)
            else:
                downtime_last_week += time_diff.total_seconds() / 3600
                if (now - current_timestamp).days < 1:
                    downtime_last_day += time_diff.total_seconds() / 3600
                if (now - current_timestamp).total_seconds() <= 3600:
                    downtime_last_hour += min(time_diff.total_seconds() / 60, 60)

        last_status = entry.status
        last_timestamp = current_timestamp

    # Calculate for the remaining time until 'now'
    if is_business_hour(now):
        time_diff = calculate_business_hours(last_timestamp, now)
        if last_status == 'active':
            uptime_last_week += time_diff.total_seconds() / 3600
            uptime_last_day += time_diff.total_seconds() / 3600
            uptime_last_hour += min(time_diff.total_seconds() / 60, 60)
        else:
            downtime_last_week += time_diff.total_seconds() / 3600
            downtime_last_day += time_diff.total_seconds() / 3600
            downtime_last_hour += min(time_diff.total_seconds() / 60, 60)

    # Calculate total business hours for the last week
    total_business_hours = sum(
        calculate_business_hours(now.replace(hour=0, minute=0, second=0) - timedelta(days=i),
                                 now.replace(hour=23, minute=59, second=59) - timedelta(days=i)).total_seconds() / 3600
        for i in range(7)
    )

    # Adjust uptime and downtime
    uptime_last_week = min(uptime_last_week, total_business_hours)
    downtime_last_week = min(downtime_last_week, total_business_hours)
    
    # Ensure uptime + downtime = total business hours for the week
    if uptime_last_week + downtime_last_week < total_business_hours:
        uptime_last_week = total_business_hours - downtime_last_week

    return {
        'uptime_last_hour': round(min(uptime_last_hour, 60), 2),
        'uptime_last_day': round(min(uptime_last_day, 24), 2),
        'uptime_last_week': round(uptime_last_week, 2),
        'downtime_last_hour': round(min(downtime_last_hour, 60), 2),
        'downtime_last_day': round(min(downtime_last_day, 24), 2),
        'downtime_last_week': round(downtime_last_week, 2)
    }
