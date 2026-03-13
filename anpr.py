# Imports
import cv2
import sqlite3
import time
import json
import requests
from datetime import datetime

import numpy as np
from ultralytics import YOLO
import easyocr

from picamera2 import Picamera2
from libcamera import Transform

# Config
MODEL_PATH = "uklpr.pt"
OUTPUT_JSON = "plates_log.json"

DVSA_API_KEY = "YOUR_DVSA_API_KEY_HERE"  # Get yours from https://developer-portal.driver-vehicle-licensing.api.gov.uk/
DVSA_URL = "https://driver-vehicle-licensing.api.gov.uk/vehicle-enquiry/v1/vehicles"

CAMERA_ROTATE_180 = False
CONFIDENCE_THRESHOLD = 0.5
OCR_CONF_THRESHOLD = 0.4

# Models
print("Loading YOLO model...")
model = YOLO(MODEL_PATH)

print("Loading OCR reader...")
reader = easyocr.Reader(["en"], gpu=False)

# Initialise Camera
print("Initializing camera...")

picam2 = Picamera2()

config = picam2.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    transform=Transform(rotation=180 if CAMERA_ROTATE_180 else 0)
)

picam2.configure(config)
picam2.start()

# Helpers
seen_plates = set()

def clean_plate(text: str) -> str:
    text = text.upper()
    text = "".join(c for c in text if c.isalnum())
    return text

def dvsa_lookup(plate: str):
    headers = {
        "x-api-key": DVSA_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "ANPR-Pi-Research/1.0"
    }
    payload = {"registrationNumber": plate}

    try:
        r = requests.post(DVSA_URL, headers=headers, json=payload, timeout=5)
        if r.status_code == 200:
            return r.json()
        else:
            return {"error": f"DVSA returned {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}

def log_plate(plate, confidence, dvsa_data):
    record = {
        "plate": plate,
        "confidence": confidence,
        "timestamp": datetime.utcnow().isoformat(),
        "dvsa": dvsa_data
    }

    try:
        with open(OUTPUT_JSON, "r") as f:
            data = json.load(f)
    except:
        data = []

    data.append(record)

    with open(OUTPUT_JSON, "w") as f:
        json.dump(data, f, indent=2)

# Speed Measurement Setup
SPEED_DISTANCE_METERS = 10.0  # Distance between the two horizontal gates in meters

GATE_Y1 = 400  # Start gate Y-coordinate
GATE_Y2 = 450  # End gate Y-coordinate

vehicle_times = {}  # Keyed by plate: {"t1": ..., "t2": ...}

# Main Loop
print("Starting live ANPR. Press Q to quit.")

while True:
    frame = picam2.capture_array()
    results = model(frame, verbose=False)[0]

    if results.boxes is not None:
        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < CONFIDENCE_THRESHOLD:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            plate_crop = frame[y1:y2, x1:x2]

            ocr_results = reader.readtext(plate_crop)

            for (_, text, ocr_conf) in ocr_results:
                if ocr_conf < OCR_CONF_THRESHOLD:
                    continue

                plate = clean_plate(text)
                if len(plate) < 5:
                    continue
                if plate in seen_plates:
                    continue

                seen_plates.add(plate)
                print(f"[PLATE] {plate} ({conf:.2f})")

                dvsa_data = dvsa_lookup(plate)
                log_plate(plate, conf, dvsa_data)

                # Write to SQLite
                try:
                    conn = sqlite3.connect("vehicles.db")
                    cursor = conn.cursor()
                    cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vehicles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        registration_number TEXT,
                        tax_status TEXT,
                        tax_due_date TEXT,
                        mot_status TEXT,
                        make TEXT,
                        colour TEXT,
                        year_of_manufacture INTEGER
                    )
                    """)
                    conn.commit()

                    dvsa_info = dvsa_data if isinstance(dvsa_data, dict) else {}
                    vehicle_record = {
                        "registration_number": dvsa_info.get("registrationNumber"),
                        "tax_status": dvsa_info.get("taxStatus"),
                        "tax_due_date": dvsa_info.get("taxDueDate"),
                        "mot_status": dvsa_info.get("motStatus"),
                        "make": dvsa_info.get("make"),
                        "colour": dvsa_info.get("colour"),
                        "year_of_manufacture": dvsa_info.get("yearOfManufacture")
                    }

                    cursor.execute("""
                    INSERT INTO vehicles 
                    (registration_number, tax_status, tax_due_date, mot_status, make, colour, year_of_manufacture)
                    VALUES (:registration_number, :tax_status, :tax_due_date, :mot_status, :make, :colour, :year_of_manufacture)
                    """, vehicle_record)

                    conn.commit()
                    print("Vehicle info saved successfully!")
                except Exception as e:
                    print(f"Failed to save vehicle info: {e}")
                finally:
                    try:
                        conn.close()
                    except:
                        pass

                # Speed Calculation
                plate_center_y = (y1 + y2) // 2

                if plate not in vehicle_times:
                    if plate_center_y > GATE_Y1:
                        vehicle_times[plate] = {"t1": time.time()}
                elif "t2" not in vehicle_times[plate]:
                    if plate_center_y > GATE_Y2:
                        vehicle_times[plate]["t2"] = time.time()
                        delta_t = vehicle_times[plate]["t2"] - vehicle_times[plate]["t1"]
                        speed_m_s = SPEED_DISTANCE_METERS / delta_t
                        speed_kmh = speed_m_s * 3.6
                        print(f"[SPEED] {plate}: {speed_kmh:.2f} km/h")

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, plate, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

    # Speed Gates
    cv2.line(frame, (0, GATE_Y1), (frame.shape[1], GATE_Y1), (255, 0, 0), 2)  # Start gate - blue
    cv2.line(frame, (0, GATE_Y2), (frame.shape[1], GATE_Y2), (0, 0, 255), 2)  # End gate - red

    cv2.imshow("ANPR Live", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# Clean up
cv2.destroyAllWindows()
picam2.stop()
print("Stopped.")