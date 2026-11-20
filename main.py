"""
Lab Booking Request Sorter
==========================
Course: CIT AI-Native Engineering Programme · Semester 1 · Assessment 5 (Capstone)
Author: Student

Zero-dependency standard library implementation:
- Uses ONLY Python built-in standard libraries (os, csv, json, re, datetime, urllib).
- Works immediately on ANY Python installation without requiring 'pip install'.
- Connects directly to Groq Cloud API via Python's native urllib.request.
- Fully offline-resilient: if GROQ_API_KEY is not set or network is unreachable,
  it smoothly uses the deterministic fallback rules so it never crashes!

Outputs produced:
1. results.csv  - Every request with status and reason
2. schedule.csv - Tentative available schedule sorted by date
3. issues.csv   - Unbookable requests with reasons
4. summary.txt  - Aggregated counts per status and lab
"""

import os
import csv
import json
import re
from datetime import datetime
import urllib.request
import urllib.error


# ==========================================
# 0. BUILT-IN .ENV FILE LOADER (No pip needed)
# ==========================================

def load_local_env(env_path=".env"):
    """
    Reads a local .env file and sets environment variables without needing python-dotenv.
    """
    if not os.path.exists(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("\"'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


# Load .env file automatically
load_local_env(".env")


# ==========================================
# CONFIGURATION
# ==========================================
SEMESTER_START = os.getenv("SEMESTER_START", "2026-10-01")
SEMESTER_END = os.getenv("SEMESTER_END", "2026-12-15")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()


# ==========================================
# 1. FILE LOADING FUNCTIONS
# ==========================================

def load_system_prompt(filepath="system_prompt.txt"):
    """
    Reads the system prompt file built on the 5-role framework.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"[Warning] System prompt file '{filepath}' not found.")
        return "Extract lab, date (YYYY-MM-DD), slot (FN/AN), students, and summary as valid JSON."


def load_labs(filepath="labs.csv"):
    """
    Loads laboratory definitions and capacities into a dictionary.
    Returns: { "LAB1": {"name": "Python Lab 1", "capacity": 60}, ... }
    """
    labs = {}
    if not os.path.exists(filepath):
        print(f"[Error] Lab file '{filepath}' not found.")
        return labs

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["code"].strip()
            name = row["name"].strip()
            capacity = int(row["capacity"].strip())
            labs[code] = {"name": name, "capacity": capacity}
    return labs


def load_bookings(filepath="bookings.csv"):
    """
    Loads existing confirmed bookings from the register.
    Returns: set of (date, slot, lab) tuples.
    NOTE: bookings.csv is strictly read-only and never modified.
    """
    bookings = set()
    if not os.path.exists(filepath):
        print(f"[Warning] Bookings file '{filepath}' not found.")
        return bookings

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row["date"].strip()
            slot = row["slot"].strip()
            lab = row["lab"].strip()
            bookings.add((date_str, slot, lab))
    return bookings


def load_requests(filepath="requests.csv"):
    """
    Loads booking requests from requests.csv in order.
    Returns: list of dicts [{'id': 'Q01', 'sent': '2026-10-08', 'request': '...'}, ...]
    """
    requests = []
    if not os.path.exists(filepath):
        print(f"[Error] Requests file '{filepath}' not found.")
        return requests

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            requests.append({
                "id": row["id"].strip(),
                "sent": row["sent"].strip(),
                "request": row["request"].strip()
            })
    return requests


# ==========================================
# 2. LLM CALL & EXTRACTION (Native urllib)
# ==========================================

def call_groq_api(system_prompt, user_request, api_key):
    """
    Calls the Groq Cloud API using standard Python urllib (no external libraries needed).
    Uses JSON response format for guaranteed structured output.
    """
    if not api_key or api_key == "gsk_your_actual_groq_api_key_here":
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "LabBookingSorter/1.0"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request}
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def is_valid(data, valid_lab_codes):
    """
    Validates that the extracted dictionary adheres strictly to the required schema:
    1. Must be a dict.
    2. Must contain exactly the 5 required keys.
    3. Lab must be in valid_lab_codes or None.
    4. Slot must be 'FN', 'AN', or None.
    5. Students must be positive int or None.
    6. Date must be YYYY-MM-DD string or None.
    7. Summary must be string or None.
    """
    if not isinstance(data, dict):
        return False

    required_keys = {"lab", "date", "slot", "students", "summary"}
    if set(data.keys()) != required_keys:
        return False

    lab = data.get("lab")
    if lab is not None and lab not in valid_lab_codes:
        return False

    slot = data.get("slot")
    if slot is not None and slot not in ("FN", "AN"):
        return False

    students = data.get("students")
    if students is not None and (not isinstance(students, int) or students <= 0):
        return False

    date_val = data.get("date")
    if date_val is not None:
        if not isinstance(date_val, str) or not re.match(r"^\d{4}-\d{2}-\d{2}$", date_val):
            return False

    summary = data.get("summary")
    if summary is not None and not isinstance(summary, str):
        return False

    return True


def fallback_extraction(request_text, valid_labs):
    """
    Deterministic rule-based fallback when LLM is unavailable or offline.
    Extracts explicit lab codes, slots, dates, and student numbers safely.
    """
    result = {
        "lab": None,
        "date": None,
        "slot": None,
        "students": None,
        "summary": "Extraction fallback"
    }

    req_upper = request_text.upper()

    # Lab check
    for code, info in valid_labs.items():
        if code in req_upper or info["name"].upper() in req_upper:
            if "PYTHON LAB" in req_upper and "PYTHON LAB 1" not in req_upper and "PYTHON LAB 2" not in req_upper and "LAB1" not in req_upper and "LAB2" not in req_upper:
                result["lab"] = None
                break
            result["lab"] = code
            break

    # Slot check
    if "AFTERNOON" in req_upper or "AN" in req_upper.split() or "PM" in req_upper:
        result["slot"] = "AN"
    elif "FORENOON" in req_upper or "MORNING" in req_upper or "FN" in req_upper.split() or "AM" in req_upper:
        result["slot"] = "FN"

    # Explicit date check (e.g., '15 October', '16 Oct', '31 February')
    month_map = {
        "OCTOBER": "10", "OCT": "10",
        "NOVEMBER": "11", "NOV": "11",
        "DECEMBER": "12", "DEC": "12",
        "FEBRUARY": "02", "FEB": "02"
    }
    date_match = re.search(r"(\b\d{1,2}\b)\s+(October|Oct|November|Nov|December|Dec|February|Feb)", request_text, re.IGNORECASE)
    if date_match:
        day_str = str(int(date_match.group(1))).zfill(2)
        month_str = month_map.get(date_match.group(2).upper(), "10")
        result["date"] = f"2026-{month_str}-{day_str}"

    # Student count check (e.g. '55 students')
    student_match = re.search(r"(\b\d{1,3}\b)\s*(?:students|people|participants)", request_text, re.IGNORECASE)
    if student_match:
        result["students"] = int(student_match.group(1))

    # Summary
    words = request_text.split()
    result["summary"] = " ".join(words[:10])

    return result


def classify(system_prompt, request_text, valid_labs, api_key=GROQ_API_KEY):
    """
    Sends request to Groq API, validates schema, retries once on invalid reply,
    and falls back safely if both attempts fail.
    """
    valid_codes = set(valid_labs.keys())

    # Attempt 1: Groq API Call
    raw_response = call_groq_api(system_prompt, request_text, api_key)
    if raw_response:
        try:
            data = json.loads(raw_response)
            if is_valid(data, valid_codes):
                return {
                    "lab": data["lab"],
                    "date": data["date"],
                    "slot": data["slot"],
                    "students": data["students"],
                    "summary": data.get("summary", "")[:100]
                }
        except Exception:
            pass

        # Attempt 2: Retry once if invalid
        retry_prompt = system_prompt + "\n\nCRITICAL: Return ONLY valid JSON with keys: lab, date, slot, students, summary."
        raw_response_2 = call_groq_api(retry_prompt, request_text, api_key)
        if raw_response_2:
            try:
                data = json.loads(raw_response_2)
                if is_valid(data, valid_codes):
                    return {
                        "lab": data["lab"],
                        "date": data["date"],
                        "slot": data["slot"],
                        "students": data["students"],
                        "summary": data.get("summary", "")[:100]
                    }
            except Exception:
                pass

    # Safe fallback if API key is not yet set or offline
    return fallback_extraction(request_text, valid_labs)


# ==========================================
# 3. FACT CHECKING & STATUS DECISION RULES
# ==========================================

def check_date(date_str, semester_start, semester_end):
    """
    Checks whether date_str is a real calendar date and within semester bounds.
    Returns: (is_valid: bool, datetime_obj or None, error_message or "")
    """
    if not date_str:
        return False, None, "Missing date"

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False, None, f"Invalid calendar date '{date_str}'"

    start_dt = datetime.strptime(semester_start, "%Y-%m-%d")
    end_dt = datetime.strptime(semester_end, "%Y-%m-%d")

    if not (start_dt <= dt <= end_dt):
        return False, None, f"Date {date_str} outside semester ({semester_start} to {semester_end})"

    return True, dt, ""


def check_facts_grounded(extracted, original_text):
    """
    Grounding check (anti-hallucination):
    - Verifies day number extracted actually appears in the request text.
    - Verifies student count extracted actually appears in the request text.
    """
    date_val = extracted.get("date")
    if date_val:
        day_str = date_val.split("-")[-1]
        day_num = str(int(day_str))
        pattern = r"\b" + day_num + r"(?:st|nd|rd|th)?\b"
        if not re.search(pattern, original_text, re.IGNORECASE):
            return False, f"Day '{day_num}' was not explicitly mentioned in request text"

    students_val = extracted.get("students")
    if students_val is not None:
        pattern = r"\b" + str(students_val) + r"\b"
        if not re.search(pattern, original_text):
            return False, f"Student count '{students_val}' was not found in request text"

    return True, ""


def decide(extracted, original_text, labs, confirmed_bookings, tentative_held_slots):
    """
    Decides the booking status following the EXACT required order:
    1. Check facts first (Real date, semester bounds, grounded day & student numbers).
    2. needs_more_info: lab, date, slot or students is missing.
    3. lab_closed: date is a Sunday.
    4. over_capacity: requested students > lab capacity.
    5. conflict: slot already occupied in bookings.csv OR earlier in current run.
    6. available: all checks pass. Slot is held in tentative_held_slots.
    """
    lab = extracted.get("lab")
    date_str = extracted.get("date")
    slot = extracted.get("slot")
    students = extracted.get("students")

    # RULE 1: Check facts first
    if date_str is not None:
        valid_date, dt_obj, err_msg = check_date(date_str, SEMESTER_START, SEMESTER_END)
        if not valid_date:
            return "needs_more_info", err_msg

    grounded, ground_err = check_facts_grounded(extracted, original_text)
    if not grounded:
        return "needs_more_info", f"Fact check failed: {ground_err}"

    # RULE 2: needs_more_info
    missing_fields = []
    if not lab:
        missing_fields.append("lab")
    if not date_str:
        missing_fields.append("date")
    if not slot:
        missing_fields.append("slot")
    if students is None:
        missing_fields.append("students")

    if missing_fields:
        return "needs_more_info", f"Missing or unclear details: {', '.join(missing_fields)}"

    # RULE 3: lab_closed
    dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
    if dt_obj.weekday() == 6:  # 6 = Sunday
        return "lab_closed", f"Laboratories are closed on Sundays ({date_str} is Sunday)"

    # RULE 4: over_capacity
    lab_info = labs.get(lab)
    if not lab_info:
        return "needs_more_info", f"Lab code '{lab}' not recognized in labs master"

    capacity = lab_info["capacity"]
    if students > capacity:
        return "over_capacity", f"Requested {students} students, but {lab} capacity is only {capacity}"

    # RULE 5: conflict
    slot_key = (date_str, slot, lab)
    if slot_key in confirmed_bookings:
        return "conflict", f"Slot already confirmed for {lab} on {date_str} ({slot}) in register"

    if slot_key in tentative_held_slots:
        prev_id = tentative_held_slots[slot_key]
        return "conflict", f"Slot clash with earlier accepted request {prev_id} on {date_str} ({slot})"

    # RULE 6: available
    return "available", "All requirements met; slot is available"


# ==========================================
# 4. REPORT WRITING
# ==========================================

def write_reports(processed_records, labs, output_dir="."):
    """
    Generates all four required output files.
    """
    # 1. results.csv
    results_path = os.path.join(output_dir, "results.csv")
    with open(results_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "sent", "lab", "date", "slot", "students", "status", "reason"])
        for item in processed_records:
            writer.writerow([
                item["id"],
                item["sent"],
                item["lab"] or "",
                item["date"] or "",
                item["slot"] or "",
                item["students"] or "",
                item["status"],
                item["reason"]
            ])

    # 2. schedule.csv (Available requests sorted by date and slot)
    schedule_path = os.path.join(output_dir, "schedule.csv")
    available_items = [i for i in processed_records if i["status"] == "available"]
    available_items.sort(key=lambda x: (x["date"], x["slot"], x["lab"]))
    with open(schedule_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "slot", "lab", "students", "request_id", "summary"])
        for item in available_items:
            writer.writerow([
                item["date"],
                item["slot"],
                item["lab"],
                item["students"],
                item["id"],
                item["summary"]
            ])

    # 3. issues.csv (All non-available requests)
    issues_path = os.path.join(output_dir, "issues.csv")
    issue_items = [i for i in processed_records if i["status"] != "available"]
    with open(issues_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "sent", "request", "status", "reason"])
        for item in issue_items:
            writer.writerow([
                item["id"],
                item["sent"],
                item["request"],
                item["status"],
                item["reason"]
            ])

    # 4. summary.txt (Counts by status and by lab)
    summary_path = os.path.join(output_dir, "summary.txt")
    total_requests = len(processed_records)
    
    status_counts = {
        "available": 0,
        "conflict": 0,
        "over_capacity": 0,
        "lab_closed": 0,
        "needs_more_info": 0
    }
    for item in processed_records:
        status_counts[item["status"]] = status_counts.get(item["status"], 0) + 1

    lab_counts = {code: 0 for code in labs.keys()}
    for item in available_items:
        if item["lab"] in lab_counts:
            lab_counts[item["lab"]] += 1

    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("LAB BOOKING REQUEST SORTER - SUMMARY REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total Requests Processed : {total_requests}\n")
        f.write(f"Configured Semester Range: {SEMESTER_START} to {SEMESTER_END}\n\n")
        
        f.write("REQUEST COUNTS BY STATUS:\n")
        f.write("-" * 40 + "\n")
        for status, count in status_counts.items():
            f.write(f"  - {status:<18}: {count}\n")
        f.write("\n")

        f.write("AVAILABLE BOOKINGS BY LAB:\n")
        f.write("-" * 40 + "\n")
        for code, count in lab_counts.items():
            lab_name = labs[code]["name"]
            f.write(f"  - {code} ({lab_name:<16}): {count} bookings\n")
        f.write("\n")
        f.write("IMPORTANT NOTICE:\n")
        f.write("The software NEVER confirms bookings automatically.\n")
        f.write("The lab in-charge must confirm all tentative bookings.\n")
        f.write("=" * 60 + "\n")


# ==========================================
# 5. MAIN ORCHESTRATOR
# ==========================================

def main():
    print("=" * 60)
    print("Lab Booking Request Sorter")
    print("CIT AI-Native Engineering Programme · Capstone")
    print("=" * 60)

    # 1. Load system prompt and CSV files
    print("\n[Step 1] Loading input files...")
    system_prompt = load_system_prompt("system_prompt.txt")
    labs = load_labs("labs.csv")
    confirmed_bookings = load_bookings("bookings.csv")
    requests = load_requests("requests.csv")

    print(f"Loaded {len(labs)} labs.")
    print(f"Loaded {len(confirmed_bookings)} confirmed bookings from register.")
    print(f"Loaded {len(requests)} incoming requests from requests.csv.")

    # 2. Check API Key Status
    print("\n[Step 2] Checking Groq API Status...")
    if GROQ_API_KEY and GROQ_API_KEY != "gsk_your_actual_groq_api_key_here":
        print(f"Groq API Key detected! Model: {GROQ_MODEL}")
    else:
        print("Note: Running in rule-based fallback mode (offline / demo ready).")

    # 3. Process requests
    print("\n[Step 3] Processing requests through Decision Engine...")
    processed_records = []
    tentative_held_slots = {}

    for idx, req in enumerate(requests, start=1):
        req_id = req["id"]
        raw_text = req["request"]
        sent_date = req["sent"]

        print(f"\nProcessing [{idx}/{len(requests)}] {req_id}: '{raw_text[:50]}...'")

        # Extraction
        extracted = classify(system_prompt, raw_text, labs, GROQ_API_KEY)
        print(f"  Extracted: Lab={extracted.get('lab')}, Date={extracted.get('date')}, "
              f"Slot={extracted.get('slot')}, Students={extracted.get('students')}")

        # Decision
        status, reason = decide(extracted, raw_text, labs, confirmed_bookings, tentative_held_slots)
        print(f"  Status   : -> {status.upper()} ({reason})")

        # Hold slot if available
        if status == "available":
            slot_key = (extracted["date"], extracted["slot"], extracted["lab"])
            tentative_held_slots[slot_key] = req_id

        record = {
            "id": req_id,
            "sent": sent_date,
            "request": raw_text,
            "lab": extracted.get("lab"),
            "date": extracted.get("date"),
            "slot": extracted.get("slot"),
            "students": extracted.get("students"),
            "summary": extracted.get("summary", ""),
            "status": status,
            "reason": reason
        }
        processed_records.append(record)

    # 4. Generate all four output reports
    print("\n[Step 4] Writing output reports...")
    write_reports(processed_records, labs, output_dir=".")
    print("  -> results.csv generated.")
    print("  -> schedule.csv generated.")
    print("  -> issues.csv generated.")
    print("  -> summary.txt generated.")

    print("\n" + "=" * 60)
    print("Processing Complete! Human Checkpoint: The lab in-charge must confirm every booking.")
    print("=" * 60)


if __name__ == "__main__":
    main()
