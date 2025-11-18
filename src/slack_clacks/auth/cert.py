import os
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from slack_clacks.configuration.database import get_config_dir


def get_cert_paths(config_dir: str | Path | None = None) -> tuple[Path, Path]:
    """Get paths to certificate and key files."""
    config_path = get_config_dir(config_dir)
    cert_path = config_path / "localhost.crt"
    key_path = config_path / "localhost.key"
    return cert_path, key_path


def generate_self_signed_cert(
    config_dir: str | Path | None = None,
) -> tuple[Path, Path]:
    """Generate a self-signed certificate for localhost."""
    cert_path, key_path = get_cert_paths(config_dir)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Clacks"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(IPv4Address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    os.chmod(key_path, 0o600)

    return cert_path, key_path


def ensure_cert_exists(config_dir: str | Path | None = None) -> tuple[Path, Path]:
    """Ensure certificate exists, generate if not."""
    cert_path, key_path = get_cert_paths(config_dir)

    if not cert_path.exists() or not key_path.exists():
        return generate_self_signed_cert(config_dir)

    return cert_path, key_path


def get_cert_info(config_dir: str | Path | None = None) -> dict | None:
    """Get information about the current certificate."""
    cert_path, key_path = get_cert_paths(config_dir)

    if not cert_path.exists():
        return None

    with open(cert_path, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())

    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "not_valid_before": cert.not_valid_before_utc,
        "not_valid_after": cert.not_valid_after_utc,
        "serial_number": cert.serial_number,
        "cert_path": str(cert_path),
        "key_path": str(key_path),
    }
