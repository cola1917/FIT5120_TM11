from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.load_env import ensure_dotenv_loaded
from app.routers import recommendations

ensure_dotenv_loaded()

app = FastAPI(title="NutriHealth API")

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(recommendations.router)


@app.get("/")
def hello_world():
    return {"hello": "world"}
