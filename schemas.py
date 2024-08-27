from pydantic import BaseModel

class ReportResponse(BaseModel):
    report_id: str

class ReportStatus(BaseModel):
    status: str
    csv_data: str = None