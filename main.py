from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import seed_database
from routers import auth, menu, tables, reservations, pos, kitchen, management, reports

app = FastAPI(
    title="Johnny's Dining & Bar API",
    description="FastAPI backend for the React restaurant website and POS",
    version="2.0.0"
)

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(menu.router)
app.include_router(tables.router)
app.include_router(reservations.router)
app.include_router(pos.router)
app.include_router(kitchen.router)
app.include_router(management.router)
app.include_router(reports.router)

@app.on_event("startup")
def on_startup():
    # Ensure database tables and initial seed data are populated
    seed_database()

@app.get("/")
def root():
    return {
        "status": "online",
        "restaurant": "Johnny's Dining & Bar",
        "api_docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
