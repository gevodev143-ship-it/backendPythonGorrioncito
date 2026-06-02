from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.excelbd_routes          import router as excel_router
from app.routes.respuesta_modelo_router import router as modelo_router

app = FastAPI(
    title="Ferretería Gorrioncito API",
    version="1.0.0",
    description="Backend API con FastAPI + Supabase"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://localhost:3000",
        "http://localhost:5173",
        "https://ferreteriagorrioncito-red.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Insertados",
        "X-Duplicados",
        "Content-Disposition"
    ],
)

app.include_router(excel_router,     tags=["Excel"])
app.include_router(modelo_router,    tags=["Modelo"])

@app.get("/")
def root():
    return {"message": "API Ferretería Gorrioncito funcionando 🚀"}