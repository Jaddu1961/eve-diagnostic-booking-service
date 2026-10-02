"""python -m app.seed  -> creates tables, an admin user and sample centres/tests."""
from decimal import Decimal

from sqlalchemy import select

from .config import settings
from .database import Base, SessionLocal, engine
from .models import Centre, CentreTest, DiagnosticTest, User
from .security import hash_password


def run() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == settings.admin_email)):
            db.add(User(email=settings.admin_email, full_name="Admin",
                        hashed_password=hash_password(settings.admin_password), is_admin=True))
        if not db.scalar(select(Centre)):
            cbc = DiagnosticTest(name="Complete Blood Count", description="CBC")
            lipid = DiagnosticTest(name="Lipid Profile")
            mri = DiagnosticTest(name="MRI Brain")
            db.add_all([cbc, lipid, mri])
            db.flush()
            c1 = Centre(name="Sunrise Diagnostics", location="Ahmedabad")
            c2 = Centre(name="CityCare Labs", location="Mumbai")
            c1.offerings = [CentreTest(test_id=cbc.id, price=Decimal("350")),
                            CentreTest(test_id=lipid.id, price=Decimal("600"))]
            c2.offerings = [CentreTest(test_id=cbc.id, price=Decimal("400")),
                            CentreTest(test_id=mri.id, price=Decimal("7500"))]
            db.add_all([c1, c2])
        db.commit()
    print("Seeded.")


if __name__ == "__main__":
    run()
