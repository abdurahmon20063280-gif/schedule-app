from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = "sqlite:///./schedule.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


class Schedule(Base):
    __tablename__ = "schedule"

    id = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, nullable=False)
    room_id = Column(Integer, nullable=False)
    group_name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    day = Column(Integer, nullable=False)
    period = Column(Integer, nullable=False)
    week_type = Column(String, nullable=False)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LessonSchema(BaseModel):
    professor_id: int
    room_id: int
    group_name: str
    subject: str
    day: int
    period: int
    week_type: str


app = FastAPI(title="Schedule Manager")


@app.get("/api/schedule")
def get_schedule(db: Session = Depends(get_db)):
    lessons = db.query(Schedule).order_by(
        Schedule.day,
        Schedule.period
    ).all()

    return [
        {
            "id": lesson.id,
            "professor_id": lesson.professor_id,
            "room_id": lesson.room_id,
            "group_name": lesson.group_name,
            "subject": lesson.subject,
            "day": lesson.day,
            "period": lesson.period,
            "week_type": lesson.week_type,
        }
        for lesson in lessons
    ]


@app.post("/api/schedule")
def add_lesson(
    lesson: LessonSchema,
    db: Session = Depends(get_db)
):
    # Проверяем преподавателя
    collision_prof = db.query(Schedule).filter(
        Schedule.professor_id == lesson.professor_id,
        Schedule.day == lesson.day,
        Schedule.period == lesson.period,
        Schedule.week_type == lesson.week_type
    ).first()

    if collision_prof:
        raise HTTPException(
            status_code=400,
            detail="Преподаватель уже занят в это время."
        )

    # Проверяем аудиторию
    collision_room = db.query(Schedule).filter(
        Schedule.room_id == lesson.room_id,
        Schedule.day == lesson.day,
        Schedule.period == lesson.period,
        Schedule.week_type == lesson.week_type
    ).first()

    if collision_room:
        raise HTTPException(
            status_code=400,
            detail="Аудитория уже занята в это время."
        )

    # Проверяем группу
    collision_group = db.query(Schedule).filter(
        Schedule.group_name == lesson.group_name,
        Schedule.day == lesson.day,
        Schedule.period == lesson.period,
        Schedule.week_type == lesson.week_type
    ).first()

    if collision_group:
        raise HTTPException(
            status_code=400,
            detail="У группы уже есть занятие в это время."
        )

    new_lesson = Schedule(
        professor_id=lesson.professor_id,
        room_id=lesson.room_id,
        group_name=lesson.group_name,
        subject=lesson.subject,
        day=lesson.day,
        period=lesson.period,
        week_type=lesson.week_type
    )

    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)

    return {
        "status": "success",
        "message": "Занятие добавлено.",
        "id": new_lesson.id
    }


@app.delete("/api/schedule/{lesson_id}")
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db)
):
    lesson = db.query(Schedule).filter(
        Schedule.id == lesson_id
    ).first()

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Занятие не найдено."
        )

    db.delete(lesson)
    db.commit()

    return {
        "status": "success",
        "message": "Занятие удалено."
    }


from fastapi.responses import FileResponse

@app.get("/")
def home():
    return FileResponse("static/index.html")


