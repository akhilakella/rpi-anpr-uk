# 🚗 RPI-ANPR-UK
### Automatic Number Plate Recognition on a Raspberry Pi 5 — with live DVSA government database lookups

Built by a 13-year-old in the UK. Runs entirely on a £70 computer.

---

## What it does

This system uses a Raspberry Pi 5 and camera module to detect and read UK number plates in real time. Every plate that passes is:

- **Detected** using a YOLO model trained specifically on UK licence plates
- **Read** using EasyOCR to extract the registration text
- **Verified** against the real UK DVSA (Driver and Vehicle Licensing Agency) government database
- **Logged** to both a local SQLite database and a JSON file with tax status, MOT status, make, colour, and year of manufacture
- **Speed-estimated** using two virtual gate lines on the camera frame

---

## Tech Stack

| Component | Tool |
|---|---|
| Object Detection | YOLOv8 (`ultralytics`) with UK-specific model |
| OCR | EasyOCR |
| Camera | Raspberry Pi Camera Module via `picamera2` |
| Government API | DVSA Vehicle Enquiry API |
| Database | SQLite3 |
| Hardware | Raspberry Pi 5 |

---

## Features

### 🔍 YOLO + OCR Pipeline
The system runs a two-stage pipeline: YOLO first detects the bounding box of the plate in the frame, then EasyOCR reads the text from the cropped region. Both have configurable confidence thresholds to reduce false positives.

### 🏛️ Real DVSA API Integration
Every detected plate is cross-referenced against the official UK government DVSA database in real time. The system retrieves and stores:
- Tax status & due date
- MOT status
- Vehicle make & colour
- Year of manufacture

### ⚡ Speed Estimation
Two horizontal gate lines are drawn across the camera frame. When a vehicle crosses both gates, the system calculates its approximate speed in km/h based on the time delta and a configured real-world distance.

### 🗄️ Dual Logging
All detections are written to both a structured SQLite database (`vehicles.db`) and a JSON log (`plates_log.json`) with UTC timestamps.

---

## Hardware Requirements

**Recommended:**
- Raspberry Pi 5
- Raspberry Pi HQ Camera with 16mm lens

**Minimum:**
- Raspberry Pi 4
- Any compatible Raspberry Pi camera module

**Also needed:**
- Stable power supply

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/rpi-anpr-uk.git
cd rpi-anpr-uk
```

### 2. Install dependencies
```bash
pip install ultralytics easyocr picamera2 opencv-python requests numpy
```

### 3. Get a DVSA API key
Register at the [DVSA Developer Portal](https://developer-portal.driver-vehicle-licensing.api.gov.uk/) and get your free API key.

### 4. Add your API key
In `anpr.py`, replace:
```python
DVSA_API_KEY = "YOUR_DVSA_API_KEY_HERE"
```

### 5. Download the YOLO model
Place a UK licence plate YOLO model (`uklpr.pt`) in the root directory. You can train your own or find community-trained models on Roboflow/HuggingFace.

### 6. Run
```bash
python anpr.py
```
Press `Q` to quit.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `CONFIDENCE_THRESHOLD` | `0.5` | Minimum YOLO detection confidence |
| `OCR_CONF_THRESHOLD` | `0.4` | Minimum OCR confidence |
| `CAMERA_ROTATE_180` | `False` | Flip camera if mounted upside down |
| `SPEED_DISTANCE_METERS` | `10.0` | Real-world distance between speed gates (metres) |
| `GATE_Y1` / `GATE_Y2` | `400` / `450` | Y-coordinates of speed measurement gates |

---

## Output

**SQLite (`vehicles.db`):**
```
id | registration_number | tax_status | tax_due_date | mot_status | make | colour | year_of_manufacture
```

**JSON (`plates_log.json`):**
```json
{
  "plate": "AB12CDE",
  "confidence": 0.91,
  "timestamp": "2026-01-15T14:32:01.123456",
  "dvsa": {
    "taxStatus": "Taxed",
    "motStatus": "Valid",
    "make": "FORD",
    "colour": "BLUE",
    "yearOfManufacture": 2019
  }
}
```

---

## Disclaimer

This project is for **educational and research purposes only**. Ensure you comply with UK data protection laws (UK GDPR) and do not use this system to collect data on vehicles or individuals without appropriate legal basis. The DVSA API is provided for legitimate vehicle enquiry use only.

---

## Author

**Akhil** — 13-year-old developer from Rugby, UK.
BBC CWR Young Hero Award recipient.

*Built with a Raspberry Pi, curiosity, and way too many late nights.*
