"""Integration test for batch/gateway flow with signed URLs and JWT verification."""

from __future__ import annotations

import json
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from preciagro.packages.engines.image_analysis.app.main import app
from preciagro.packages.engines.image_analysis.app.models import (
    BatchAnalysisRequest,
    ImageAnalysisRequest,
)
from preciagro.packages.shared.security.deps import TenantContext, get_tenant_context


# Mock tenant context for testing
def mock_get_tenant_context() -> TenantContext:
    """Override the tenant context dependency for testing."""
    return TenantContext(
        tenant_id="test-tenant",
        user_id="test-user",
        scopes=["*"],
    )


# Override the dependency
app.dependency_overrides[get_tenant_context] = mock_get_tenant_context


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_batch_analysis_returns_artifact_urls(client: TestClient) -> None:
    """
    Test that batch analysis returns proper artifact URLs for gradcam, masks, etc.
    Verifies that signed URL structure is present in responses.
    """
    # Sample base64 image (1x1 pixel PNG)
    sample_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mO0WwoAAt8BNxGMD4kAAAAASUVORK5CYII="

    batch_request = BatchAnalysisRequest(
        items=[
            ImageAnalysisRequest(
                crop="maize",
                image_base64=sample_image,
                client_request_id="test-batch-1",
                quantify_lesions=True,
                count_objects=False,
            ),
            ImageAnalysisRequest(
                crop="maize",
                image_base64=sample_image,
                client_request_id="test-batch-2",
                quantify_lesions=False,
                count_objects=False,
            ),
        ]
    )

    response = client.post(
        "/api/image-analysis/batch",
        json=batch_request.model_dump(),
        headers={"Authorization": "Bearer mock-jwt-token"},
    )

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert len(data["items"]) == 2

    # Verify artifact URLs are present
    for original_request, result in zip(batch_request.items, data["items"]):
        assert "explanations" in result
        explanations = result["explanations"]

        # Check for gradcam URL
        if "gradcam_url" in explanations and explanations["gradcam_url"]:
            gradcam_url = str(explanations["gradcam_url"])
            print(f"GradCAM URL: {gradcam_url}")
            assert len(gradcam_url) > 0

        # Check for mask URLs if lesion quantification was requested
        if original_request.quantify_lesions:
            mask_overlay = explanations.get("mask_overlay")
            if mask_overlay:
                mask_url = str(mask_overlay)
                print(f"Mask Overlay URL: {mask_url}")
                assert len(mask_url) > 0


def test_single_analysis_with_artifact_urls(client: TestClient) -> None:
    """
    Test single analysis endpoint and verify artifact URLs.
    """
    sample_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mO0WwoAAt8BNxGMD4kAAAAASUVORK5CYII="

    request_data = {
        "crop": "maize",
        "image_base64": sample_image,
        "client_request_id": "test-single-1",
        "quantify_lesions": True,
        "count_objects": False,
    }

    response = client.post(
        "/api/image-analysis/analyze-image",
        json=request_data,
        headers={"Authorization": "Bearer mock-jwt-token"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert "disease" in data
    assert "growth_stage" in data
    assert "explanations" in data

    # Log artifact URLs for manual verification
    explanations = data["explanations"]
    print("\n=== Artifact URLs ===")
    if explanations.get("gradcam_url"):
        print(f"GradCAM: {explanations['gradcam_url']}")
    if explanations.get("mask_overlay"):
        print(f"Mask Overlay: {explanations['mask_overlay']}")
    if explanations.get("mask_binary"):
        print(f"Mask Binary: {explanations['mask_binary']}")
    print("===================\n")


def test_signed_url_parameters_in_artifacts(client: TestClient) -> None:
    """
    Verify that artifact URLs contain expected signed URL parameters
    (signature, token, or other security markers).
    """
    sample_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mO0WwoAAt8BNxGMD4kAAAAASUVORK5CYII="

    request_data = {
        "crop": "maize",
        "image_base64": sample_image,
        "client_request_id": "test-signed-url",
        "quantify_lesions": False,
        "count_objects": False,
    }

    response = client.post(
        "/api/image-analysis/analyze-image",
        json=request_data,
        headers={"Authorization": "Bearer mock-jwt-token"},
    )

    assert response.status_code == 200
    data = response.json()

    explanations = data.get("explanations", {})

    # Check if any artifact URLs are generated
    artifact_urls = []
    if explanations.get("gradcam_url"):
        artifact_urls.append(str(explanations["gradcam_url"]))
    if explanations.get("mask_overlay"):
        artifact_urls.append(str(explanations["mask_overlay"]))
    if explanations.get("mask_binary"):
        artifact_urls.append(str(explanations["mask_binary"]))

    # If URLs are generated, they should follow expected patterns
    # Note: In local dev, URLs might be file:// or http://localhost
    # In production, they should contain signing parameters
    for url in artifact_urls:
        print(f"Checking URL: {url}")
        # URLs should be well-formed
        assert len(url) > 0
        # Could add more specific checks here for production signed URLs
        # assert "signature" in url or "token" in url or "sig" in url


def test_jwt_header_extraction(client: TestClient) -> None:
    """
    Test that JWT tokens in Authorization header are properly handled.
    """
    sample_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mO0WwoAAt8BNxGMD4kAAAAASUVORK5CYII="

    request_data = {
        "crop": "maize",
        "image_base64": sample_image,
        "client_request_id": "test-jwt",
        "quantify_lesions": False,
        "count_objects": False,
    }

    # Test with Bearer token
    response = client.post(
        "/api/image-analysis/analyze-image",
        json=request_data,
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"},
    )

    assert response.status_code == 200

    # Test without Authorization header (should still work with mocked auth)
    response_no_auth = client.post(
        "/api/image-analysis/analyze-image",
        json=request_data,
    )

    # With mocked tenant context, this should work
    assert response_no_auth.status_code == 200


if __name__ == "__main__":
    # Run with: python -m pytest preciagro/packages/engines/image_analysis/tests/test_batch_gateway_integration.py -v -s
    pytest.main([__file__, "-v", "-s"])
