"""Generate self-signed SSL certificates for development."""

import os
import subprocess
import sys
from pathlib import Path


def generate_self_signed_cert(output_dir: str = "certs"):
    """Generate self-signed SSL certificate for development.
    
    Args:
        output_dir: Directory to store certificates
    """
    # Create certs directory
    cert_path = Path(output_dir)
    cert_path.mkdir(exist_ok=True)
    
    cert_file = cert_path / "cert.pem"
    key_file = cert_path / "key.pem"
    
    # Check if certificates already exist
    if cert_file.exists() and key_file.exists():
        print(f"✓ Certificates already exist in {output_dir}")
        print(f"  - Certificate: {cert_file}")
        print(f"  - Private key: {key_file}")
        return
    
    print("Generating self-signed SSL certificate...")
    print("⚠️  WARNING: This is for DEVELOPMENT ONLY. Do not use in production!")
    
    try:
        # Generate self-signed certificate using openssl
        cmd = [
            "openssl", "req", "-x509",
            "-newkey", "rsa:4096",
            "-keyout", str(key_file),
            "-out", str(cert_file),
            "-days", "365",
            "-nodes",  # No password
            "-subj", "/C=US/ST=State/L=City/O=PreciagroMVP/CN=localhost"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Certificate generated successfully!")
            print(f"  - Certificate: {cert_file}")
            print(f"  - Private key: {key_file}")
            print(f"\n📝 To use HTTPS, set environment variable:")
            print(f"     ENABLE_HTTPS=true")
            print(f"     SSL_CERT_FILE={cert_file.absolute()}")
            print(f"     SSL_KEY_FILE={key_file.absolute()}")
        else:
            print(f"❌ Error generating certificate:")
            print(result.stderr)
            sys.exit(1)
            
    except FileNotFoundError:
        print("❌ OpenSSL not found. Please install OpenSSL:")
        print("   Windows: choco install openssl")
        print("   macOS: brew install openssl")
        print("   Linux: sudo apt-get install openssl")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    generate_self_signed_cert()
