from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "dev"
    CIE_ENGINE_NAME: str = "crop_intelligence"
    # External services
    WEATHER_BASE_URL: str = ""
    SOIL_BASE_URL: str = ""
    SATELLITE_BASE_URL: str = ""
    # Feature flags
    ENABLE_ML_PHOTO_CLASSIFIER: bool = True
    ENABLE_BANDIT_N_TIMING: bool = False

settings = Settings()
