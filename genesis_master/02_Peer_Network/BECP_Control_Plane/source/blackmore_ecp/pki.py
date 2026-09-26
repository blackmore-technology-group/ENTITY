from __future__ import annotations

import base64
import ipaddress
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def _canonical_hello(device_id: str, timestamp: int, nonce: str) -> bytes:
    return json.dumps(
        {"device_id": device_id, "timestamp": timestamp, "nonce": nonce},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def certificate_fingerprint(path: str) -> str:
    cert = x509.load_pem_x509_certificate(Path(path).read_bytes())
    return cert.fingerprint(hashes.SHA256()).hex()

def sign_device_hello(private_key_path: str, device_id: str, timestamp: int, nonce: str) -> str:
    key = serialization.load_pem_private_key(Path(private_key_path).read_bytes(), password=None)
    signature = key.sign(
        _canonical_hello(device_id, timestamp, nonce),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def verify_device_hello(
    certificate_path: str,
    device_id: str,
    timestamp: int,
    nonce: str,
    signature_b64: str,
    max_clock_skew_seconds: int = 120,
) -> None:
    if abs(int(time.time()) - int(timestamp)) > max_clock_skew_seconds:
        raise PermissionError("device authentication timestamp outside permitted skew")
    cert = x509.load_pem_x509_certificate(Path(certificate_path).read_bytes())
    signature = base64.b64decode(signature_b64)
    cert.public_key().verify(
        signature,
        _canonical_hello(device_id, timestamp, nonce),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )

def _write_key(key: rsa.RSAPrivateKey, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def create_ca(directory: str, common_name: str = "Blackmore BECP Root CA") -> dict[str, str]:
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    key_path = root / "ca.key.pem"
    cert_path = root / "ca.cert.pem"
    if key_path.exists() and cert_path.exists():
        return {"key": str(key_path), "cert": str(cert_path)}
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=1), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    _write_key(key, key_path)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return {"key": str(key_path), "cert": str(cert_path)}


def _san_entries(names: list[str] | None) -> list[x509.GeneralName]:
    entries: list[x509.GeneralName] = []
    for value in names or []:
        try:
            entries.append(x509.IPAddress(ipaddress.ip_address(value)))
        except ValueError:
            entries.append(x509.DNSName(value))
    return entries

def issue_certificate(
    ca_key_path: str,
    ca_cert_path: str,
    output_dir: str,
    common_name: str,
    filename_prefix: str,
    client: bool = False,
    san_names: list[str] | None = None,
) -> dict[str, str]:
    ca_key = serialization.load_pem_private_key(Path(ca_key_path).read_bytes(), password=None)
    ca_cert = x509.load_pem_x509_certificate(Path(ca_cert_path).read_bytes())
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.CLIENT_AUTH if client else ExtendedKeyUsageOID.SERVER_AUTH
            ]),
            critical=False,
        )
    )
    sans = _san_entries(san_names)
    if sans:
        builder = builder.add_extension(x509.SubjectAlternativeName(sans), critical=False)
    cert = builder.sign(ca_key, hashes.SHA256())
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    key_path = root / f"{filename_prefix}.key.pem"
    cert_path = root / f"{filename_prefix}.cert.pem"
    _write_key(key, key_path)
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return {"key": str(key_path), "cert": str(cert_path)}


def certificate_summary(path: str) -> dict[str, Any]:
    cert = x509.load_pem_x509_certificate(Path(path).read_bytes())
    try:
        sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        san_values = [str(x.value) for x in sans]
    except x509.ExtensionNotFound:
        san_values = []
    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "serial_number": str(cert.serial_number),
        "not_valid_before_utc": cert.not_valid_before_utc.isoformat(),
        "not_valid_after_utc": cert.not_valid_after_utc.isoformat(),
        "sha256_fingerprint": cert.fingerprint(hashes.SHA256()).hex(),
        "subject_alt_names": san_values,
    }
