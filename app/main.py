from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routers import auth, bookings, centres, payments


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fine for an assignment; use Alembic migrations in production.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Diagnostic Booking Service",
    version="1.0.0",
    lifespan=lifespan
)

# Allow the local HTML frontend to communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(centres.router)
app.include_router(bookings.router)
app.include_router(payments.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}