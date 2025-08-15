from dotenv import load_dotenv
import os

load_dotenv()
print("OWM_API_KEY =", os.getenv("OWM_API_KEY"))
