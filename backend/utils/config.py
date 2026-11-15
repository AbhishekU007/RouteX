import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = "RouteX"
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "")
DEFAULT_CITY = "Agra, Uttar Pradesh, India"
