# RMCS Device Certificate Creation (Python)

## Overview

The **RMCS Device Certificate Creation** application is a Python-based UI tool used to generate client certificates for RMCS devices.

Each device's certificates and configuration information are saved in a dedicated folder named after its Device ID. The generated certificate chain is intended to be used by the device for mutual TLS (mTLS) authentication with the RMCS MQTT broker.

The application can be run directly from the Python source or as a standalone Windows program (`RMCS-DeviceCerts.exe`) that does not require Python to be installed.

## Project Structure

The application uses a `resources` folder to store the Root CA certificate and the Sub-CA certificate and private key.

```text
RMCS_Device_Cert_Creation_Python/
│
├── resources/
│   ├── ca.crt
│   ├── sub-ca.crt
│   └── sub-ca.key
│
├── app.py
├── certgen.py
├── requirements.txt
└── README.md
```

The project directory is located on the local system. For example:

```text
C:\Users\<USERNAME>\PycharmProjects\RMCS_Device_Cert_Creation_Python
```

The actual path depends on the system and the location where the project is stored.

Generated device certificates are **not** stored inside the project. They are saved in a separate folder outside the application (see [Output Location](#output-location)):

```text
C:\RMCS\device-certificates\
└── <DEVICE_ID>/
    ├── ca.crt
    ├── device.crt
    ├── device.key
    ├── device-chain.crt
    └── device-info.txt
```

## Prerequisites

**To run from source (`python app.py`):**

- Python installed on the system.
- The project dependencies installed (`pip install -r requirements.txt`).
- The required CA certificate and Sub-CA files available in the `resources` folder.
- The password for the Sub-CA private key, if the key is password-protected.

**To run the built program (`RMCS-DeviceCerts.exe`):**

- No Python installation is needed. The CA files are bundled inside the program.
- The password for the Sub-CA private key, if the key is password-protected.

## Required Resource Files

| File | Description |
|---|---|
| `ca.crt` | Root CA certificate used to establish the certificate trust chain. |
| `sub-ca.crt` | Subordinate CA certificate used to issue device certificates. |
| `sub-ca.key` | Sub-CA private key used to sign device certificates. Should be password-protected. |

Never place the Root CA private key (`ca.key`) in the `resources` folder.

## Running the Application

**From source:**

```powershell
python app.py
```

**As a program:** double-click `RMCS-DeviceCerts.exe`. The first start may take a few seconds while the program unpacks itself. If Windows shows "Windows protected your PC", click **More info → Run anyway** (the program is not digitally signed).

When the window opens, the grey line at the top shows where device folders will be saved. If a red **Missing in ...** message appears instead, one or more resource files are missing and the **Generate** button is disabled.

## Using the Application

### 1. Enter Device Information

Enter the device information through the UI.

| Field | Required | Default used in topics |
|---|---|---|
| Device ID | Yes | None |
| Client ID | No | `algo1` |
| Project ID | No | `rmcs1` |

- **Device ID:** Mandatory. Only alphabetic characters (`A–Z`, `a–z`) and digits (`0–9`) are allowed.
- **Client ID:** Optional. If left empty, the MQTT topics use `algo1`.
- **Project ID:** Optional. If left empty, the MQTT topics use `rmcs1`.

The Device ID is also used as the device certificate's Common Name (CN) and as the name of the device's output folder.

### 2. Generate Certificates

1. Enter the Device ID.
2. Optionally enter the Client ID and Project ID.
3. Enter the Sub-CA private key password. Click the circle next to the password field to show or hide it.
4. Click **Generate** (or press **Enter**).
5. Click **Open folder** to view the generated files.

After a successful generation, the form is cleared, including the password. Status and error messages disappear automatically after 15 seconds.

### 3. Handle Existing Device IDs

If certificates have already been generated for the same Device ID, the application first checks the Device ID and the Sub-CA password, then displays a confirmation dialog asking whether the existing certificates should be overwritten.

- **Yes:** Regenerate the certificates and replace the existing device folder. Everything in that folder is deleted.
- **No:** Do not overwrite the existing certificates. The folder is left unchanged.

Ensure that overwriting certificates will not disrupt a device that is already configured to use the existing certificate and private key. Overwriting does not revoke the old certificate; it remains valid until it expires.

## Generated Files

For each Device ID, the application creates a dedicated folder:

```text
C:\RMCS\device-certificates\<DEVICE_ID>\
```

The folder contains the following files:

| File | Description |
|---|---|
| `ca.crt` | Root CA certificate supplied for validating the MQTT server certificate. |
| `device.crt` | Individual device certificate signed by the Sub-CA. |
| `device.key` | Private key corresponding to the device certificate. |
| `device-chain.crt` | Certificate chain containing the device certificate and the Sub-CA certificate. Use this file as the device certificate file for the device connection. |
| `device-info.txt` | Contains the entered device details, certificate information, MQTTX connection settings and the MQTT topics that must be configured for the device. |

### Important: Device Certificate

Use **`device-chain.crt`** as the device certificate file when configuring the device for MQTT connectivity. The broker trusts only the Root CA, so the device must send the Sub-CA certificate along with its own certificate.

The corresponding private key is `device.key`. The device must also use `ca.crt` to validate the MQTT server certificate.

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

Each generated device certificate is valid for **825 days**. If the Sub-CA expires sooner, the device certificate ends on the same date as the Sub-CA. If the Sub-CA has already expired, the application shows an error and a new Sub-CA must be created.

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

The same location is used whether the application is run from source or as `RMCS-DeviceCerts.exe`. The folder is created automatically the first time you click **Generate**. The current location is always shown in the app window under **Device folders are saved in:**.

To use a different location, set the `RMCS_DEVICES_DIR` environment variable before starting the app, for example:

```powershell
setx RMCS_DEVICES_DIR "D:\RMCS\device-certificates"
```

Restart the app after changing it.

Because device files are kept separate from the application, updating, moving or replacing the app (or the `.exe`) does not affect existing device certificates. Each folder contains a private key (`device.key`), so keep this location private and backed up, and never add it to source control. Avoid locations synced to OneDrive or other cloud storage unless that is intended.

Each device has its own folder, keeping its certificates and configuration information separate from those of other devices.

## Building the Program (.exe)

The program is built on Windows with PyInstaller, from the project folder.

1. Install the dependencies in the project's virtual environment:

   ```powershell
   .venv\Scripts\activate
   pip install cryptography pyinstaller
   ```

2. Make sure `resources\` contains exactly `ca.crt`, `sub-ca.crt` and the password-protected `sub-ca.key`. Every file in this folder is bundled into the program.

3. Build:

   ```powershell
   pyinstaller --onefile --windowed --clean --name RMCS-DeviceCerts --add-data "resources;resources" app.py
   ```

4. The program is created at:

   ```text
   dist\RMCS-DeviceCerts.exe
   ```

   The `build\` folder and `RMCS-DeviceCerts.spec` file are build by-products and can be deleted.

5. Test it by double-clicking the `.exe`, generating a test device and checking the output folder.

**Notes:**

- The CA files are bundled inside the program. Rebuild the `.exe` whenever `ca.crt`, `sub-ca.crt` or `sub-ca.key` change, for example when the Sub-CA is renewed.
- Anything bundled in the `.exe` can be extracted by someone who has the program. This is why `sub-ca.key` must be password-protected and `ca.key` must never be included.
- If startup is slow or antivirus software flags the program, build without `--onefile`. This creates a `dist\RMCS-DeviceCerts\` folder instead; distribute the whole folder, not just the `.exe`.

## Notes

- Device ID is the only mandatory UI field.
- Device IDs may contain letters and digits only.
- Client ID defaults to `algo1` in the MQTT topics.
- Project ID defaults to `rmcs1` in the MQTT topics.
- The certificate CN matches the Device ID.
- Device certificates are valid for 825 days, or until the Sub-CA expires if sooner.
- The Sub-CA private key password must be supplied when required.
- Existing certificates are overwritten only after confirmation, and the old certificate is not revoked.
- Device folders are saved in `C:\RMCS\device-certificates` (or the `RMCS_DEVICES_DIR` location), outside the application.
- Use `device-chain.crt` as the device certificate file and `device.key` as its corresponding private key.
- Rebuild the `.exe` whenever the CA files change.