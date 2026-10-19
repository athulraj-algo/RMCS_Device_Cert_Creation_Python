# RMCS Device Certificate Creation (Python)

## Overview

The **RMCS Device Certificate Creation** application is a Python-based UI tool used to generate client certificates for RMCS devices.

Each device's certificates and configuration information are saved in a dedicated folder named after its Device ID. The generated certificate chain is intended to be used by the device for mutual TLS (mTLS) authentication with the RMCS MQTT broker.

## Project Structure

The application uses a `resources` folder to store the Root CA certificate and Sub-CA certificate and private key. Generated device certificates are saved under the project's root directory in a `devices` folder.

```text
RMCS_Device_Cert_Creation_Python/
│
├── resources/
│   ├── ca.crt
│   ├── sub-ca.crt
│   └── sub-ca.key
│
├── devices/
│   └── <DEVICE_ID>/
│       ├── ca.crt
│       ├── device.crt
│       ├── device.key
│       ├── device-chain.crt
│       └── device-info.txt
│
├── <application Python files>
└── README.md
```

The project directory is located on the local system. For example:

```text
C:\Users\<USERNAME>\PycharmProjects\RMCS_Device_Cert_Creation_Python
```

The actual path depends on the system and the location where the project is stored.

## Prerequisites

- Python installed on the system.
- The project dependencies installed.
- The required CA certificate and Sub-CA files available in the `resources` folder.
- The password for the Sub-CA private key, if the key is password-protected.

## Required Resource Files

| File | Description |
|---|---|
| `ca.crt` | Root CA certificate used to establish the certificate trust chain. |
| `sub-ca.crt` | Subordinate CA certificate used to issue device certificates. |
| `sub-ca.key` | Sub-CA private key used to sign device certificates. This key is password-protected when configured that way. |


## Using the Application

### 1. Enter Device Information

Open the application and enter the device information through the UI.

| Field | Required | Default value |
|---|---|---|
| Device ID | Yes | None |
| Client ID | No | `algo1` |
| Project ID | No | `rmcs1` |

- **Device ID:** Mandatory. Only alphabetic characters (`A–Z`, `a–z`) and digits (`0–9`) are allowed.
- **Client ID:** Optional. If left empty, the application uses `algo1`.
- **Project ID:** Optional. If left empty, the application uses `rmcs1`.

The Device ID is also used as the device certificate's Common Name (CN).

### 2. Generate Certificates

1. Enter the Device ID.
2. Optionally enter the Client ID and Project ID.
3. Provide the Sub-CA private key password when requested.
4. Click the certificate generation button.

The application generates the device certificate files and configuration information.

### 3. Handle Existing Device IDs

If certificates have already been generated for the same Device ID, the application displays a confirmation dialog asking whether the existing certificates should be overwritten.

- **Confirm:** Regenerate the certificates and overwrite the existing output files.
- **Cancel:** Do not overwrite the existing certificates.

Ensure that overwriting certificates will not disrupt a device that is already configured to use the existing certificate and private key.

## Generated Files

For each Device ID, the application creates a dedicated folder:

```text
devices/<DEVICE_ID>/
```

The folder contains the following files:

| File | Description |
|---|---|
| `ca.crt` | Root CA certificate supplied for certificate validation. |
| `device.crt` | Individual device certificate signed by the Sub-CA. |
| `device.key` | Private key corresponding to the device certificate. |
| `device-chain.crt` | Certificate chain containing the device certificate and its required CA certificate(s). Use this file as the device certificate file for the configured device connection. |
| `device-info.txt` | Contains certificate-related information and the MQTT topics that must be configured for the device. |

### Important: Device Certificate

Use **`device-chain.crt`** as the device certificate file when configuring the device for MQTT connectivity, as required by this application.

The corresponding private key is `device.key`. The device must also trust the appropriate CA certificate to validate the MQTT server certificate.

Keep `device.key` secure and do not share it publicly.

## Certificate Configuration

### Common Name (CN)

The device certificate's Common Name is set to the Device ID.

For example, if the Device ID is:

```text
A3B4C5D6
```

The certificate subject includes:

```text
CN=A3B4C5D6
```

### Certificate Validity

Each generated device certificate has a validity period of **825 days**.

## MQTT Topic Configuration

The application writes the MQTT topics into `device-info.txt` based on the Device ID, Client ID, and Project ID.

The default values are:

- Client ID: `algo1`
- Project ID: `rmcs1`

The topic structure is:

```text
TOPICS
-------------------------
uplink_topic   = cp/{client_id}/{project_id}/{device_id}/uplink
downlink_topic = cp/{client_id}/{project_id}/{device_id}/downlink
cfg_topic      = cp/{client_id}/{project_id}/{device_id}/cfg
test_topic     = cp/{client_id}/{project_id}/{device_id}/test
register_topic = cp/{client_id}/{project_id}/{device_id}/register
```

For example, if the Device ID is `A3B4C5D6` and the optional fields are left empty, the topics are:

```text
uplink_topic   = cp/algo1/rmcs1/A3B4C5D6/uplink
downlink_topic = cp/algo1/rmcs1/A3B4C5D6/downlink
cfg_topic      = cp/algo1/rmcs1/A3B4C5D6/cfg
test_topic     = cp/algo1/rmcs1/A3B4C5D6/test
register_topic = cp/algo1/rmcs1/A3B4C5D6/register
```

If a custom Client ID or Project ID is provided, the generated topics use those values instead.

Configure the device and MQTT broker to use the appropriate topics for communication.

## Output Location

Generated device files are stored outside the application, in a subfolder named after the Device ID:

```text
C:\RMCS\device-certificates\<DEVICE_ID>\
```

Example:

```text
C:\RMCS\device-certificates\A3B4C5D6\
```

The folder is created automatically the first time you click **Generate**. The current location is always shown in the app window under **Device folders are saved in:**.

To use a different location, set the `RMCS_DEVICES_DIR` environment variable before starting the app, for example:

```powershell
setx RMCS_DEVICES_DIR "D:\RMCS\device-certificates"
```

Restart the app after changing it.

Because device files are kept separate from the application, updating or replacing the app (or the `.exe`) does not affect existing device certificates. Each folder contains a private key (`device.key`), so keep this location private and backed up, and never add it to source control.

Each device has its own folder, keeping its certificates and configuration information separate from those of other devices.

## Notes

- Device ID is the only mandatory UI field.
- Device IDs may contain letters and digits only.
- Client ID defaults to `algo1`.
- Project ID defaults to `rmcs1`.
- The certificate CN matches the Device ID.
- Device certificates have a validity period of 825 days.
- The Sub-CA private key password must be supplied when required.
- Existing certificates are overwritten only after confirmation.
- Use `device-chain.crt` as the device certificate file and `device.key` as its corresponding private key.
- Protect all private keys and their passwords.
