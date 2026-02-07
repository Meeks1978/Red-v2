from fastapi import APIRouter
from app.pillars import compute_pillars

router = APIRouter()

@router.get("/health/pillars")
def pillars():
    return compute_pillars()
