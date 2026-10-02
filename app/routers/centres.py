from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import Centre, CentreTest, DiagnosticTest
from ..schemas import CentreIn, CentreOut, CentreTestIn, DiagnosticTestIn, DiagnosticTestOut

router = APIRouter(tags=["centres & tests"])


# ---------- tests catalogue ----------
@router.get("/tests/", response_model=list[DiagnosticTestOut])
def list_tests(db: Session = Depends(get_db)):
    return db.scalars(select(DiagnosticTest).order_by(DiagnosticTest.name)).all()


@router.post("/tests/", response_model=DiagnosticTestOut, status_code=201, dependencies=[Depends(require_admin)])
def create_test(body: DiagnosticTestIn, db: Session = Depends(get_db)):
    test = DiagnosticTest(**body.model_dump())
    db.add(test)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "A test with this name already exists")
    return test


# ---------- centres ----------
@router.get("/centres/", response_model=list[CentreOut])
def list_centres(
    location: str | None = Query(None, description="Case-insensitive substring match"),
    test: str | None = Query(None, description="Only centres offering a test whose name contains this"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Centre).order_by(Centre.id).limit(limit).offset(offset)
    if location:
        stmt = stmt.where(Centre.location.ilike(f"%{location}%"))
    if test:
        stmt = stmt.where(
            Centre.offerings.any(CentreTest.test.has(DiagnosticTest.name.ilike(f"%{test}%")))
        )
    return db.scalars(stmt).all()


@router.get("/centres/{centre_id}", response_model=CentreOut)
def get_centre(centre_id: int, db: Session = Depends(get_db)):
    centre = db.get(Centre, centre_id)
    if not centre:
        raise HTTPException(404, "Centre not found")
    return centre


def _attach_tests(db: Session, centre: Centre, items: list[CentreTestIn]) -> None:
    seen: set[int] = set()
    for item in items:
        if item.test_id in seen:
            raise HTTPException(422, f"Duplicate test_id {item.test_id} in request")
        seen.add(item.test_id)
        if not db.get(DiagnosticTest, item.test_id):
            raise HTTPException(404, f"Test {item.test_id} not found")
        centre.offerings.append(CentreTest(test_id=item.test_id, price=item.price))


@router.post("/centres/", response_model=CentreOut, status_code=201, dependencies=[Depends(require_admin)])
def create_centre(body: CentreIn, db: Session = Depends(get_db)):
    centre = Centre(name=body.name, location=body.location)
    db.add(centre)
    _attach_tests(db, centre, body.tests)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Centre already exists at this location")
    db.refresh(centre)
    return centre


@router.put("/centres/{centre_id}/tests", response_model=CentreOut, dependencies=[Depends(require_admin)])
def upsert_centre_test(centre_id: int, body: CentreTestIn, db: Session = Depends(get_db)):
    """Offer a test at a centre, or change its price if already offered."""
    centre = db.get(Centre, centre_id)
    if not centre:
        raise HTTPException(404, "Centre not found")
    if not db.get(DiagnosticTest, body.test_id):
        raise HTTPException(404, "Test not found")
    existing = next((o for o in centre.offerings if o.test_id == body.test_id), None)
    if existing:
        existing.price = body.price  # existing bookings keep their own amount snapshot
    else:
        centre.offerings.append(CentreTest(test_id=body.test_id, price=body.price))
    db.commit()
    db.refresh(centre)
    return centre
