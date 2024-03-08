from fastapi import FastAPI
from app.main import app

fast_app = FastAPI()
fast_app.mount("/", app)
