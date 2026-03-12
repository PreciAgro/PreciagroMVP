"""
Standalone Cloudinary upload test.
Usage: python test_upload.py <path-to-image>
"""
import sys
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
)


def test_upload(image_path: str) -> str:
    print(f"Uploading {image_path} to Cloudinary...")
    result = cloudinary.uploader.upload(
        image_path,
        folder="preciagro/test",
        resource_type="image",
    )
    url = result["secure_url"]
    print(f"Upload successful: {url}")
    return url


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_upload.py <path-to-image>")
        sys.exit(1)
    test_upload(sys.argv[1])
