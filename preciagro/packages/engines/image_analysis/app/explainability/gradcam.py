"""Grad-CAM heatmap generator for classifier explainability."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

import cv2
import numpy as np
from PIL import Image

try:  # pragma: no cover - optional heavy dep
    import torch
    from torch import nn
except ImportError:  # pragma: no cover
    torch = None
    nn = None

LOGGER = logging.getLogger(__name__)


@dataclass
class GradCAMResult:
    """Container for Grad-CAM outputs."""

    overlay_bgr: np.ndarray
    heatmap_gray: np.ndarray


class GradCAMGenerator:
    """Lightweight Grad-CAM implementation that works with timm backbones."""

    def __init__(self) -> None:
        self.device = self._resolve_device()

    @property
    def available(self) -> bool:
        return torch is not None and nn is not None

    def generate(
        self,
        bundle: dict,
        image_bgr: np.ndarray,
        target_index: int,
        transform_override: Optional[Callable] = None,
    ) -> Optional[GradCAMResult]:
        """Produce a Grad-CAM overlay for the requested target class."""

        if not self.available:
            return None

        model = bundle.get("model")
        transform = transform_override or bundle.get("transform")
        if model is None or transform is None:
            LOGGER.debug("GradCAM bundle missing model/transform")
            return None

        target_layer = self._find_target_layer(model)
        if target_layer is None:
            LOGGER.debug("Unable to locate a convolutional layer for Grad-CAM")
            return None

        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        input_tensor = transform(pil_image)
        if isinstance(input_tensor, (list, tuple)):
            input_tensor = input_tensor[0]
        if torch.is_tensor(input_tensor) is False:
            input_tensor = torch.tensor(np.array(input_tensor))
        input_tensor = input_tensor.unsqueeze(0).to(self.device)

        activations = []
        gradients = []

        def forward_hook(_, __, output):
            activations.append(output.detach())

        def backward_hook(_, grad_input, grad_output):
            gradients.append(grad_output[0].detach())

        handle_fwd = target_layer.register_forward_hook(forward_hook)
        if hasattr(target_layer, "register_full_backward_hook"):
            handle_bwd = target_layer.register_full_backward_hook(backward_hook)
        else:  # pragma: no cover - legacy torch
            handle_bwd = target_layer.register_backward_hook(
                lambda module, grad_in, grad_out: backward_hook(module, grad_in, grad_out)
            )

        model.to(self.device)
        model.zero_grad(set_to_none=True)
        try:
            with torch.enable_grad():
                logits = model(input_tensor)
                if logits.ndim == 1:
                    logits = logits.unsqueeze(0)
                score = logits[:, target_index].mean()
                score.backward()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("GradCAM forward/backward failed: %s", exc)
            return None
        finally:
            handle_fwd.remove()
            handle_bwd.remove()

        if not activations or not gradients:
            LOGGER.debug("GradCAM hooks did not capture activations/gradients")
            return None

        act = activations[-1]  # shape: [batch, channels, H, W]
        grad = gradients[-1]
        if act.ndim != 4 or grad.ndim != 4:
            LOGGER.debug("Unexpected tensor shapes for GradCAM")
            return None

        weights = grad.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * act).sum(dim=1)).squeeze(0)
        cam = cam.cpu().numpy()
        if cam.max() == 0:
            LOGGER.debug("GradCAM heatmap is empty")
            return None

        cam -= cam.min()
        cam /= (cam.max() + 1e-8)
        heatmap = cv2.resize(cam, (image_bgr.shape[1], image_bgr.shape[0]))
        colored = cv2.applyColorMap(np.uint8(255 * heatmap), cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(colored, 0.5, image_bgr, 0.5, 0)
        return GradCAMResult(overlay_bgr=overlay, heatmap_gray=(heatmap * 255).astype("uint8"))

    def _find_target_layer(self, model) -> Optional["nn.Module"]:
        """Return the last convolutional layer in the model."""

        if nn is None:
            return None

        last_conv = None
        for _, module in model.named_modules():
            if isinstance(module, nn.Conv2d):
                last_conv = module
        return last_conv

    def _resolve_device(self) -> str:
        if torch is None:
            return "cpu"
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
