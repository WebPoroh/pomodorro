# main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime, timedelta
import databases
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
import os

# SQLite database URL
DATABASE_URL = "sqlite:///./pomodoro.db"

# Create database and tables
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()
Base = declarative_base()

# SQLAlchemy models
class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    target_pomodoros = Column(Integer, default=4)
    color = Column(String, default="#d95550")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to pomodoro sessions
    pomodoros = relationship("Pomodoro", back_populates="task")

class Pomodoro(Base):
    __tablename__ = "pomodoros"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    completed_at = Column(DateTime, default=datetime.utcnow)
    duration = Column(Integer, default=25)  # in minutes

    # Relationship to task
    task = relationship("Task", back_populates="pomodoros")

# Pydantic models
class TaskCreate(BaseModel):
    name: str
    target_pomodoros: int = 4
    color: str = "#d95550"

class TaskResponse(BaseModel):
    id: int
    name: str
    target_pomodoros: int
    color: str
    is_active: bool
    completed_today: int = 0

    class Config:
        orm_mode = True

class PomodoroCreate(BaseModel):
    task_id: int
    duration: int = 25

class PomodoroResponse(BaseModel):
    id: int
    task_id: int
    completed_at: datetime
    duration: int

    class Config:
        orm_mode = True

class DailyStats(BaseModel):
    date: date
    completed: int
    tasks: dict

# Create database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)

# Session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# FastAPI app
app = FastAPI(title="Pomodoro Tracker API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API endpoints
@app.post("/tasks/", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = Task(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.get("/tasks/", response_model=List[TaskResponse])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.is_active == True).offset(skip).limit(limit).all()

    # Calculate completed pomodoros for today for each task
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())

    result = []
    for task in tasks:
        completed_today = db.query(Pomodoro).filter(
            Pomodoro.task_id == task.id,
            Pomodoro.completed_at >= today_start
        ).count()

        task_dict = {
            "id": task.id,
            "name": task.name,
            "target_pomodoros": task.target_pomodoros,
            "color": task.color,
            "is_active": task.is_active,
            "completed_today": completed_today
        }
        result.append(task_dict)

    return result

@app.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task: TaskCreate, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    for key, value in task.dict().items():
        setattr(db_task, key, value)

    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    db_task.is_active = False
    db.commit()
    return {"message": "Task deleted successfully"}

@app.post("/pomodoros/", response_model=PomodoroResponse)
def create_pomodoro(pomodoro: PomodoroCreate, db: Session = Depends(get_db)):
    # Check if task exists
    task = db.query(Task).filter(Task.id == pomodoro.task_id, Task.is_active == True).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db_pomodoro = Pomodoro(**pomodoro.dict())
    db.add(db_pomodoro)
    db.commit()
    db.refresh(db_pomodoro)
    return db_pomodoro

@app.get("/stats/daily/")
def get_daily_stats(start_date: date, end_date: date = None, db: Session = Depends(get_db)):
    if not end_date:
        end_date = start_date

    # Initialize result dictionary
    result = {}
    current_date = start_date

    while current_date <= end_date:
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())

        # Get all pomodoros for this day
        pomodoros = db.query(Pomodoro).filter(
            Pomodoro.completed_at >= day_start,
            Pomodoro.completed_at <= day_end
        ).all()

        # Count by task
        task_counts = {}
        for pomodoro in pomodoros:
            task_name = pomodoro.task.name
            task_counts[task_name] = task_counts.get(task_name, 0) + 1

        result[str(current_date)] = {
            "completed": len(pomodoros),
            "tasks": task_counts
        }

        current_date += timedelta(days=1)

    return result

@app.get("/stats/monthly/")
def get_monthly_stats(year: int, month: int, db: Session = Depends(get_db)):
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)

    return get_daily_stats(start_date, end_date, db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)