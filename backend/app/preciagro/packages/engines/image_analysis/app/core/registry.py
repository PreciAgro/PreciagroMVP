"""Config and label registry loaders for the Image Analysis Engine."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config"
MODELS_PATH = CONFIG_ROOT / "models.yaml"
LABELS_PATH = CONFIG_ROOT / "labels.yaml"
PROMPT_DIR = CONFIG_ROOT / "prompts"


class QualityThresholdConfig(BaseModel):
    """Threshold configuration for the quality gate."""

    blur_threshold: float = 120.0
    exposure_min: float = 0.2
    exposure_max: float = 0.85
    min_resolution: int = 640
    center_focus_min: float = 0.85


class ClassifierConfig(BaseModel):
    """Backbone configuration for the primary classifier."""

    name: str
    weights_path: str
    threshold: float = 0.6
    top_k: int = 3
    tta: bool = False


class ClipConfig(BaseModel):
    """CLIP fallback configuration."""

    enabled: bool = False
    model_name: str = "ViT-B-32"
    pretrained: str = "openai"
    similarity_threshold: float = 0.5
    prompt_file: Optional[str] = None


class SegmentationConfig(BaseModel):
    """SAM/SAM2 segmentation configuration."""

    enabled: bool = False
    model: Optional[str] = None
    weights_path: Optional[str] = None
    weights_uri: Optional[str] = None


class CountingConfig(BaseModel):
    """YOLO counting configuration."""

    enabled: bool = False
    model: Optional[str] = None
    weights_path: Optional[str] = None
    weights_uri: Optional[str] = None
    classes: List[str] = Field(default_factory=list)


class CropModelConfig(BaseModel):
    """Top-level configuration for a crop."""

    classifier: ClassifierConfig
    clip: ClipConfig = Field(default_factory=ClipConfig)
    segmentation: SegmentationConfig = Field(default_factory=SegmentationConfig)
    counting: CountingConfig = Field(default_factory=CountingConfig)
    quality: QualityThresholdConfig = Field(default_factory=QualityThresholdConfig)

    def prompt_file(self) -> Optional[str]:
        """Return the prompt file configured for this crop, if any."""

        if self.clip and self.clip.prompt_file:
            return self.clip.prompt_file
        return None


class ModelRegistry(BaseModel):
    """Registry containing crop-specific configs."""

    crops: Dict[str, CropModelConfig]
    default_crop: str = "maize"

    def get_crop(self, crop_name: str | None) -> CropModelConfig:
        """Return the config for a crop, defaulting to the configured fallback."""

        if not self.crops:
            msg = "Model registry has no crop definitions"
            raise ValueError(msg)

        normalized = (crop_name or "").lower()
        if normalized in self.crops:
            return self.crops[normalized]

        fallback = self.default_crop.lower()
        if fallback not in self.crops:
            fallback = next(iter(self.crops.keys()))
        return self.crops[fallback]


class DiseaseLabel(BaseModel):
    """Disease label metadata."""

    code: str
    label: str
    aliases: List[str] = Field(default_factory=list)
    crops: List[str] = Field(default_factory=list)


class GrowthStageLabel(BaseModel):
    """Growth stage metadata."""

    code: str
    label: str
    crops: List[str] = Field(default_factory=list)


class LabelRegistry(BaseModel):
    """Lookup utilities for disease and growth stage codes."""

    diseases: Dict[str, DiseaseLabel]
    alias_map: Dict[str, str]
    growth_stages: Dict[str, GrowthStageLabel]
    crop_stage_lookup: Dict[str, str]

    def disease_code_for(self, label: str | None) -> str:
        """Resolve various label spellings to internal codes."""

        if not label:
            return "CIE.DZ.UNKNOWN"
        return self.alias_map.get(label.lower(), "CIE.DZ.UNKNOWN")

    def growth_stage_for_crop(self, crop: str | None) -> GrowthStageLabel | None:
        """Return the preferred growth-stage label for a crop."""

        if not crop:
            return None
        stage_code = self.crop_stage_lookup.get(crop.lower())
        if not stage_code:
            return None
        return self.growth_stages.get(stage_code)


class PromptSet(BaseModel):
    """Curated textual prompts for CLIP fallback scoring."""

    disease_prompts: List[str] = Field(default_factory=list)
    nutrient_prompts: List[str] = Field(default_factory=list)
    general_prompts: List[str] = Field(default_factory=list)


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        msg = f"Config file not found: {path}"
        raise FileNotFoundError(msg)
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


@lru_cache(maxsize=1)
def get_model_registry() -> ModelRegistry:
    """Load and cache the model registry."""

    data = _load_yaml(MODELS_PATH)
    raw_crops = data.get("crops", {})
    normalized: Dict[str, CropModelConfig] = {}
    for crop_name, crop_cfg in raw_crops.items():
        normalized[crop_name.lower()] = CropModelConfig(**crop_cfg)

    default_crop = (data.get("default_crop") or next(iter(normalized.keys()))).lower()
    return ModelRegistry(crops=normalized, default_crop=default_crop)


@lru_cache(maxsize=1)
def get_label_registry() -> LabelRegistry:
    """Load and cache disease / growth stage mappings."""

    data = _load_yaml(LABELS_PATH)
    diseases: Dict[str, DiseaseLabel] = {}
    alias_map: Dict[str, str] = {}

    for entry in data.get("diseases", []):
        label = DiseaseLabel(**entry)
        diseases[label.code] = label
        alias_map[label.label.lower()] = label.code
        for alias in label.aliases:
            alias_map[alias.lower()] = label.code

    growth_stages: Dict[str, GrowthStageLabel] = {}
    crop_stage_lookup: Dict[str, str] = {}
    for entry in data.get("growth_stages", []):
        stage = GrowthStageLabel(**entry)
        growth_stages[stage.code] = stage
        for crop in stage.crops:
            crop_stage_lookup[crop.lower()] = stage.code

    return LabelRegistry(
        diseases=diseases,
        alias_map=alias_map,
        growth_stages=growth_stages,
        crop_stage_lookup=crop_stage_lookup,
    )


@lru_cache(maxsize=32)
def get_prompt_set(crop: str | None) -> PromptSet:
    """Load prompt sets for a crop if configured."""

    if not crop:
        return PromptSet()

    registry = get_model_registry()
    crop_cfg = registry.get_crop(crop)
    prompt_file = crop_cfg.prompt_file()
    if not prompt_file:
        return PromptSet()

    path = (PROMPT_DIR / prompt_file).resolve()
    if not path.exists():
        return PromptSet()

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    return PromptSet(**data)
