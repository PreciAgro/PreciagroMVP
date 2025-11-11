from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "dev"
    CIE_ENGINE_NAME: str = "crop_intelligence"
    DATABASE_URL: str = "sqlite:///./cie.db"
    AUTO_CREATE_SCHEMA: bool = True
    SERVICE_AUTH_TOKEN: str = ""
    HTTP_TIMEOUT_SECONDS: float = 5.0
    API_AUTH_TOKEN: str = ""
    ENABLE_PROMETHEUS: bool = True
    # External services
    WEATHER_BASE_URL: str = ""
    SOIL_BASE_URL: str = ""
    SATELLITE_BASE_URL: str = ""
    GEOCONTEXT_BASE_URL: str = ""
    DATA_INTEGRATION_BASE_URL: str = ""
    TEMPORAL_LOGIC_BASE_URL: str = ""
    IMAGE_ANALYSIS_BASE_URL: str = ""
    # Feature flags
    ENABLE_ML_PHOTO_CLASSIFIER: bool = True
    ENABLE_BANDIT_N_TIMING: bool = False


settings = Settings()
