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
    return {"message": "IdeaDiagram AI API", "status": "online"}




# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from fastapi.responses import FileResponse
# from app.core.database import init_db
# from app.api.v1.endpoints import diagram, auth
# import os

# app = FastAPI(title="IdeaDiagram AI", version="2.0.0")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
# app.include_router(diagram.router, prefix="/api/v1/diagram", tags=["diagram"])

# @app.on_event("startup")
# def startup():
#     init_db()

# # مسیر فرانت
# FRONTEND_DIR = "E:\\Diagram_LLm\\frontend"

# @app.get("/")
# async def root():
#     return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

# @app.get("/login.html")
# async def login():
#     return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

# @app.get("/index.html")
# async def index():
#     return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# @app.get("/register.html")
# async def register():
#     return FileResponse(os.path.join(FRONTEND_DIR, "register.html"))

# app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
# app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")





# # cd E:\Diagram_LLm\backend
# # uvicorn app.main:app --reload --port 54321