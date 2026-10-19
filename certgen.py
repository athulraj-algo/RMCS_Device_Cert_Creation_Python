"""
Certificate generation for RMCS devices.

Loads the bundled CA files (root ca.crt, sub-CA device-ca.crt / device-ca.key)
and issues one client certificate per device into <output>/<device_id>/.

No UI code lives here, so it can be tested and reused on its own.
"""

import datetime
import re
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT_CERT_FILE = "ca.crt"
SUB_CA_CERT_FILE = "sub-ca.crt"
SUB_CA_KEY_FILE = "sub-ca.key"

DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{1,64}$")
VALIDITY_DAYS = 825


@dataclass
class DeviceInfo:
    device_id: str
    client_id: str = ""
    project_id: str = ""


@dataclass
class CABundle:
    root_cert: x509.Certificate
    sub_cert: x509.Certificate
    sub_key: rsa.RSAPrivateKey


# ------------------------------------------------------------------
# Loading the CA files
# ------------------------------------------------------------------

def load_ca_bundle(resources_dir, password):
    """Load and sanity-check the root CA, sub-CA cert and sub-CA key."""
    resources_dir = Path(resources_dir)

    root_cert = x509.load_pem_x509_certificate(_read(resources_dir, ROOT_CERT_FILE))
    sub_cert = x509.load_pem_x509_certificate(_read(resources_dir, SUB_CA_CERT_FILE))
    sub_key = _load_sub_ca_key(_read(resources_dir, SUB_CA_KEY_FILE), password)

    if sub_key.public_key().public_numbers() != sub_cert.public_key().public_numbers():
        raise ValueError(
            f"{SUB_CA_KEY_FILE} does not match {SUB_CA_CERT_FILE}. "
            "Make sure both files come from the same sub-CA."
        )

    try:
        sub_cert.verify_directly_issued_by(root_cert)
    except (ValueError, TypeError, InvalidSignature):
        raise ValueError(
            f"{SUB_CA_CERT_FILE} is not signed by {ROOT_CERT_FILE}. "
            "Make sure the sub-CA was created from this root CA."
        )

    return CABundle(root_cert=root_cert, sub_cert=sub_cert, sub_key=sub_key)


def _read(folder, name):
    path = folder / name
    if not path.is_file():
        raise FileNotFoundError(f"Missing {name} in {folder}")
    return path.read_bytes()


def _load_sub_ca_key(data, password):
    pw = password.encode("utf-8") if password else None
    try:
        return serialization.load_pem_private_key(data, password=pw)
    except TypeError:
        if pw is None:
            raise ValueError(
                f"{SUB_CA_KEY_FILE} is password-protected. Enter the sub-CA key password."
            )
        # A password was typed but the key is not encrypted: load it anyway.
        return serialization.load_pem_private_key(data, password=None)
    except ValueError:
        raise ValueError(f"Wrong password for {SUB_CA_KEY_FILE}.")


# ------------------------------------------------------------------
# Issuing a device certificate
# ------------------------------------------------------------------

def device_folder_exists(output_dir, device_id):
    """True if a folder for this device ID already exists in output_dir."""
    return (Path(output_dir) / device_id).exists()


def issue_device(bundle, info, output_dir, overwrite=False):
    """Create <output_dir>/<device_id>/ with key, certs and device-info.txt.

    The certificate is valid for 825 days, or until the sub-CA expires if
    that comes sooner. Returns the new folder. Nothing is left behind on failure.

    If the folder already exists, FileExistsError is raised unless
    overwrite=True, in which case the whole folder is replaced. The old
    folder is only removed after the new one is complete.
    """
    validate_device_info(info)
    output_dir = Path(output_dir)
    final_folder = output_dir / info.device_id
    if final_folder.exists() and not overwrite:
        raise FileExistsError(
            f"A folder for device '{info.device_id}' already exists: {final_folder}"
        )

    now = datetime.datetime.now(datetime.timezone.utc)
    sub_ca_expiry = bundle.sub_cert.not_valid_after_utc
    if sub_ca_expiry <= now:
        raise ValueError(
            f"The sub-CA expired on {sub_ca_expiry:%Y-%m-%d}. "
            "Create a new sub-CA before issuing device certificates."
        )
    not_after = min(now + datetime.timedelta(days=VALIDITY_DAYS), sub_ca_expiry)

    device_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    device_cert = _build_device_cert(bundle, info.device_id, device_key, now, not_after)

    output_dir.mkdir(parents=True, exist_ok=True)
    temp_folder = Path(tempfile.mkdtemp(prefix=f".{info.device_id}-", dir=output_dir))
    try:
        _write_files(temp_folder, bundle, info, device_key, device_cert)
        if final_folder.exists():
            _swap_in(temp_folder, final_folder)
        else:
            temp_folder.rename(final_folder)
    except BaseException:
        shutil.rmtree(temp_folder, ignore_errors=True)
        raise
    return final_folder


def _swap_in(new_folder, final_folder):
    """Replace final_folder with new_folder, restoring the old one on failure."""
    backup = final_folder.with_name(f".{final_folder.name}-old-{new_folder.name[-8:]}")
    try:
        final_folder.rename(backup)
    except PermissionError:
        raise PermissionError(
            f"Cannot replace {final_folder}. Close any program or window using "
            "files in that folder (for example File Explorer or MQTTX) and try again."
        )
    try:
        new_folder.rename(final_folder)
    except BaseException:
        backup.rename(final_folder)  # put the old folder back
        raise
    shutil.rmtree(backup, ignore_errors=True)


def validate_device_info(info):
    """Raise ValueError if the device details are not valid."""
    if not DEVICE_ID_PATTERN.match(info.device_id or ""):
        raise ValueError(
            "Device ID must be 1-64 characters using only letters and digits."
        )


def _build_device_cert(bundle, device_id, device_key, not_before, not_after):
    # Keep C/ST/L/O/OU from the sub-CA, replace CN with the device ID.
    attributes = [
        attr for attr in bundle.sub_cert.subject if attr.oid != NameOID.COMMON_NAME
    ]
    attributes.append(x509.NameAttribute(NameOID.COMMON_NAME, device_id))

    try:
        sub_ski = bundle.sub_cert.extensions.get_extension_for_class(
            x509.SubjectKeyIdentifier
        ).value
        authority_key_id = x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(sub_ski)
    except x509.ExtensionNotFound:
        authority_key_id = x509.AuthorityKeyIdentifier.from_issuer_public_key(
            bundle.sub_key.public_key()
        )

    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name(attributes))
        .issuer_name(bundle.sub_cert.subject)
        .public_key(device_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before - datetime.timedelta(minutes=1))
        .not_valid_after(not_after)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(device_key.public_key()), critical=False
        )
        .add_extension(authority_key_id, critical=False)
        .sign(bundle.sub_key, hashes.SHA256())
    )
    cert.verify_directly_issued_by(bundle.sub_cert)  # sanity check before saving
    return cert


def _pem(cert):
    return cert.public_bytes(serialization.Encoding.PEM)


def _write_files(folder, bundle, info, device_key, device_cert):
    (folder / "device.key").write_bytes(
        device_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (folder / "device.crt").write_bytes(_pem(device_cert))
    (folder / "device-chain.crt").write_bytes(_pem(device_cert) + _pem(bundle.sub_cert))
    (folder / "ca.crt").write_bytes(_pem(bundle.root_cert))
    (folder / "device-info.txt").write_text(
        _info_text(bundle, info, device_cert), encoding="utf-8"
    )


def _info_text(bundle, info, cert):
    def cn(name):
        values = name.get_attributes_for_oid(NameOID.COMMON_NAME)
        return values[0].value if values else str(name)

    fingerprint = cert.fingerprint(hashes.SHA256()).hex(":").upper()
    generated = datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    not_set_client = "algo1"
    not_set_prj = "rmcs1"

    return f"""RMCS DEVICE CERTIFICATE
=======================

Device
------
Device ID    : {info.device_id}
Client ID    : {info.client_id or not_set_client}
Project ID   : {info.project_id or not_set_prj}

Certificate
-----------
Name (CN)    : {cn(cert.subject)}
Issued by    : {cn(cert.issuer)}
Root CA      : {cn(bundle.root_cert.subject)}
Serial       : {cert.serial_number:X}
Valid from   : {cert.not_valid_before_utc:%Y-%m-%d %H:%M} UTC
Valid until  : {cert.not_valid_after_utc:%Y-%m-%d %H:%M} UTC
SHA-256      : {fingerprint}

Files in this folder
--------------------
device.key         Device private key. SECRET - never share or upload it.
device.crt         Device certificate on its own.
device-chain.crt   Device certificate + sub-CA. Use this as the client certificate.
ca.crt             Root CA. Lets the device check it is talking to the real EMQX.
device-info.txt    This file.

MQTTX connection settings
-------------------------
Client ID                : {info.client_id or info.device_id}
SSL/TLS                  : On
SSL Secure               : On
Certificate              : Self signed
CA File                  : ca.crt
Client Certificate File  : device-chain.crt
Client Key File          : device.key



TOPICS
-------------------------
uplink_topic = cp/{info.client_id or 'algo1'}/{info.project_id or 'rmcs1'}/{info.device_id}/uplink
downlink_topic = cp/{info.client_id or 'algo1'}/{info.project_id or 'rmcs1'}/{info.device_id}/downlink
cfg_topic = cp/{info.client_id or 'algo1'}/{info.project_id or 'rmcs1'}/{info.device_id}/cfg
test_topic = cp/{info.client_id or 'algo1'}/{info.project_id or 'rmcs1'}/{info.device_id}/test
register_topic = cp/{info.client_id or 'algo1'}/{info.project_id or 'rmcs1'}/{info.device_id}/register

Generated: {generated}
"""