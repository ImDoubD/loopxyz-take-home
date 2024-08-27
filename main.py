from fastapi import APIRouter, FastAPI, Depends, BackgroundTasks, HTTPException, Header
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
from database import get_db
from models import Timezone, Report
from uuid import uuid4
from utils import calculate_uptime_downtime
from starlette.concurrency import run_in_threadpool
import asyncio
import csv
import schemas
import traceback
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()
router = APIRouter()

class ReportStatus:
    def __init__(self):
        self.status = "Running"
        self.csv_file_path = None

report_statuses = {}

@app.post("/trigger_report", response_model=schemas.ReportResponse)
async def trigger_report(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        report_id = str(uuid4())
        report_statuses[report_id] = ReportStatus()

        async def generate_report():
            try:
                store_ids_query = await db.execute(select(Timezone.store_id).distinct())
                store_ids_result = store_ids_query.fetchall()
                store_ids = [row[0] for row in store_ids_result]

                async def process_store(store_id):
                    result = await calculate_uptime_downtime(store_id, db)
                    if result:
                        report_entry = Report(
                            report_id=report_id,
                            store_id=store_id,
                            uptime_last_hour=result['uptime_last_hour'],
                            uptime_last_day=result['uptime_last_day'],
                            uptime_last_week=result['uptime_last_week'],
                            downtime_last_hour=result['downtime_last_hour'],
                            downtime_last_day=result['downtime_last_day'],
                            downtime_last_week=result['downtime_last_week']
                        )
                        db.add(report_entry)

                await asyncio.gather(*(process_store(store_id) for store_id in store_ids))
                await db.commit()
                print(f"Report {report_id} generated successfully")
                report_statuses[report_id].status = "Complete"
            except Exception as e:
                print(f"Error in background task: {str(e)}")
                print(traceback.format_exc())
                report_statuses[report_id].status = "Error"

        background_tasks.add_task(generate_report)
        return {"report_id": report_id, "status": "Report generation started"}
    except Exception as e:
        print(f"Error in trigger_report: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An error occurred while initiating the report generation")

async def generate_report_csv(db: AsyncSession, report_id: str):
    csv_file_path = f"report_{report_id}.csv"

    try:
        query = select(Report).filter(Report.report_id == report_id)
        result = await db.execute(query)
        report_data = result.scalars().all()
        
        with open(csv_file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['store_id', 'uptime_last_hour', 'uptime_last_day', 'uptime_last_week',
                             'downtime_last_hour', 'downtime_last_day', 'downtime_last_week'])
            
            for row in report_data:
                writer.writerow([
                    row.store_id,
                    row.uptime_last_hour,
                    f"{row.uptime_last_day:.2f}",
                    f"{row.uptime_last_week:.2f}",
                    row.downtime_last_hour,
                    f"{row.downtime_last_day:.2f}",
                    f"{row.downtime_last_week:.2f}"
                ])
        
        return csv_file_path
    except Exception as e:
        print(f"Error in generate_report_csv: {str(e)}")
        print(traceback.format_exc())
        return None

@app.get("/get_report/{report_id}")
async def get_report(report_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    try:
        if report_id not in report_statuses:
            # Check if the report exists in the database
            query = select(Report).filter(Report.report_id == report_id)
            result = await db.execute(query)
            report_exists = result.scalar_one_or_none()
            if not report_exists:
                raise HTTPException(status_code=404, detail="Report not found")
            
            # If report exists in database but not in report_statuses, it means the processing is complete
            report_statuses[report_id] = ReportStatus(status="Complete")
        
        status = report_statuses[report_id]
        
        if status.status == "Running":
            return {"status": "Running"}
        elif status.status == "Complete":
            csv_file_path = await generate_report_csv(db, report_id)
            
            if csv_file_path is None or not Path(csv_file_path).exists():
                raise HTTPException(status_code=500, detail="CSV file generation failed")
            
            # Clean up
            del report_statuses[report_id]
            
            # Add task to remove the file after it has been sent
            background_tasks.add_task(lambda: Path(csv_file_path).unlink(missing_ok=True))
            
            return FileResponse(csv_file_path, media_type='text/csv', filename=f"report_{report_id}.csv")
        elif status.status == "Error":
            # Clean up the status for this report
            del report_statuses[report_id]
            raise HTTPException(status_code=500, detail="An error occurred while generating the report")
    except Exception as e:
        print(f"Error in get_report: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="An error occurred while processing the report")