# main.py
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.orm import declarative_base
import asyncio
import os
import json

# SQLite database URL
DATABASE_URL = "sqlite:///./pomodoro.db"

# Create database and tables
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
    pomodoros = relationship("Pomodoro", back_populates="task")

class Pomodoro(Base):
    __tablename__ = "pomodoros"
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    completed_at = Column(DateTime, default=datetime.utcnow)
    duration = Column(Integer, default=25)
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

class PomodoroCreate(BaseModel):
    task_id: int
    duration: int = 25

class PomodoroResponse(BaseModel):
    id: int
    task_id: int
    completed_at: datetime
    duration: int

    model_config = ConfigDict(from_attributes=True)

class TimerState:
    def __init__(self):
        self.is_running = False
        self.is_work_time = True
        self.time_left = 1500  # 25 minutes in seconds
        self.work_duration = 1500
        self.break_duration = 300
        self.current_task_id = None

    def to_dict(self):
        return {
            "is_running": self.is_running,
            "is_work_time": self.is_work_time,
            "time_left": self.time_left,
            "work_duration": self.work_duration,
            "break_duration": self.break_duration,
            "current_task_id": self.current_task_id
        }

# Create database engine
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)

# Session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Global state for timer
timer_state = TimerState()
active_connections = []

# Background task for timer
async def timer_background_task():
    while True:
        await asyncio.sleep(1)

        if timer_state.is_running and timer_state.time_left > 0:
            timer_state.time_left -= 1

            # Notify all connected clients
            for connection in active_connections:
                try:
                    await connection.send_json({
                        "type": "timer_update",
                        "data": timer_state.to_dict()
                    })
                except:
                    # Remove disconnected clients
                    if connection in active_connections:
                        active_connections.remove(connection)

            # Timer completed
            if timer_state.time_left == 0:
                timer_state.is_running = False

                # Notify completion
                for connection in active_connections:
                    try:
                        await connection.send_json({
                            "type": "timer_complete",
                            "is_work_time": timer_state.is_work_time
                        })
                    except:
                        if connection in active_connections:
                            active_connections.remove(connection)

                # Switch mode
                if timer_state.is_work_time:
                    # Add completed pomodoro to database
                    if timer_state.current_task_id:
                        db = SessionLocal()
                        try:
                            db_pomodoro = Pomodoro(
                                task_id=timer_state.current_task_id,
                                duration=timer_state.work_duration // 60
                            )
                            db.add(db_pomodoro)
                            db.commit()
                        finally:
                            db.close()

                    # Switch to break time
                    timer_state.is_work_time = False
                    timer_state.time_left = timer_state.break_duration
                else:
                    # Switch to work time
                    timer_state.is_work_time = True
                    timer_state.time_left = timer_state.work_duration

                # Notify mode change
                for connection in active_connections:
                    try:
                        await connection.send_json({
                            "type": "mode_change",
                            "is_work_time": timer_state.is_work_time
                        })
                    except:
                        if connection in active_connections:
                            active_connections.remove(connection)

# FastAPI app
app = FastAPI(title="Pomodoro Tracker API")

# Serve static files
app.mount("/static", StaticFiles(directory="."), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
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

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Send current state on connection
        await websocket.send_json({
            "type": "initial_state",
            "timer": timer_state.to_dict()
        })

        while True:
            data = await websocket.receive_json()

            # Handle different commands
            if data.get("type") == "start_timer":
                timer_state.is_running = True
            elif data.get("type") == "pause_timer":
                timer_state.is_running = False
            elif data.get("type") == "skip_timer":
                timer_state.is_running = False
                timer_state.is_work_time = not timer_state.is_work_time
                timer_state.time_left = (
                    timer_state.break_duration
                    if timer_state.is_work_time
                    else timer_state.work_duration
                )
            elif data.get("type") == "update_settings":
                timer_state.work_duration = data.get("work_duration", 1500)
                timer_state.break_duration = data.get("break_duration", 300)
                timer_state.time_left = (
                    timer_state.work_duration
                    if timer_state.is_work_time
                    else timer_state.break_duration
                )
            elif data.get("type") == "set_task":
                timer_state.current_task_id = data.get("task_id")

            # Broadcast new state to all clients
            for connection in active_connections:
                try:
                    await connection.send_json({
                        "type": "timer_update",
                        "data": timer_state.to_dict()
                    })
                except:
                    if connection in active_connections:
                        active_connections.remove(connection)

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

# Serve the frontend
@app.get("/")
async def read_index():
    return FileResponse("index.html")

# API endpoints
@app.post("/api/tasks/", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = Task(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return task_response_with_stats(db_task, db)

@app.get("/api/tasks/", response_model=List[TaskResponse])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = db.query(Task).filter(Task.is_active == True).offset(skip).limit(limit).all()
    return [task_response_with_stats(task, db) for task in tasks]

@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task: TaskCreate, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task.dict().items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return task_response_with_stats(db_task, db)

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.is_active = False
    db.commit()
    return {"message": "Task deleted successfully"}

@app.post("/api/pomodoros/", response_model=PomodoroResponse)
def create_pomodoro(pomodoro: PomodoroCreate, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == pomodoro.task_id, Task.is_active == True).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_pomodoro = Pomodoro(**pomodoro.dict())
    db.add(db_pomodoro)
    db.commit()
    db.refresh(db_pomodoro)
    return db_pomodoro

@app.get("/api/stats/daily/")
def get_daily_stats(start_date: date, end_date: Optional[date] = None, db: Session = Depends(get_db)):
    if not end_date:
        end_date = start_date
    result = {}
    current_date = start_date
    while current_date <= end_date:
        day_start = datetime.combine(current_date, datetime.min.time())
        day_end = datetime.combine(current_date, datetime.max.time())
        pomodoros = db.query(Pomodoro).filter(
            Pomodoro.completed_at >= day_start,
            Pomodoro.completed_at <= day_end
        ).all()
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

@app.get("/api/stats/monthly/")
def get_monthly_stats(year: int, month: int, db: Session = Depends(get_db)):
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    return get_daily_stats(start_date, end_date, db)

@app.get("/api/timer/")
def get_timer_state():
    return timer_state.to_dict()

@app.post("/api/timer/start/")
def start_timer():
    timer_state.is_running = True
    return {"message": "Timer started"}

@app.post("/api/timer/pause/")
def pause_timer():
    timer_state.is_running = False
    return {"message": "Timer paused"}

@app.post("/api/timer/skip/")
def skip_timer():
    timer_state.is_running = False
    timer_state.is_work_time = not timer_state.is_work_time
    timer_state.time_left = (
        timer_state.break_duration
        if timer_state.is_work_time
        else timer_state.work_duration
    )
    return {"message": "Timer skipped"}

@app.put("/api/timer/settings/")
def update_timer_settings(work_duration: int, break_duration: int):
    timer_state.work_duration = work_duration * 60
    timer_state.break_duration = break_duration * 60
    timer_state.time_left = (
        timer_state.work_duration
        if timer_state.is_work_time
        else timer_state.break_duration
    )
    return {"message": "Timer settings updated"}

@app.put("/api/timer/task/{task_id}")
def set_current_task(task_id: int):
    timer_state.current_task_id = task_id
    return {"message": "Current task updated"}

# Helper function to add stats to task response
def task_response_with_stats(task: Task, db: Session) -> Dict[str, Any]:
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    completed_today = db.query(Pomodoro).filter(
        Pomodoro.task_id == task.id,
        Pomodoro.completed_at >= today_start
    ).count()
    return {
        "id": task.id,
        "name": task.name,
        "target_pomodoros": task.target_pomodoros,
        "color": task.color,
        "is_active": task.is_active,
        "completed_today": completed_today
    }

# Catch-all route to serve the frontend
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if os.path.exists(full_path) and os.path.isfile(full_path):
        return FileResponse(full_path)
    return FileResponse("index.html")

# Start background task on app startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(timer_background_task())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")