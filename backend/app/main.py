from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import init_db
from app.api.v1.endpoints import diagram, auth

app = FastAPI(title="IdeaDiagram AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(diagram.router, prefix="/api/v1/diagram", tags=["diagram"])

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
async def root():
    return {"message": "IdeaDiagram AI API v2.0", "status": "online"}