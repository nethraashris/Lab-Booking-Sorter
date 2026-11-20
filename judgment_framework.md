# Judgment Framework
**Project:** Lab Booking Request Sorter  
**Course:** CIT AI-Native Engineering Programme · Capstone Project  
**Author:** Student  

---

## 1. System Responsibility & Risk Matrix

| Component / Subsystem | What is the cost of being wrong? | Can the result be verified without AI? | Who is accountable? |
| :--- | :--- | :--- | :--- |
| **LLM Parameter Extraction** (`classify`, `system_prompt.txt`) | **Medium.** If the LLM hallucinates an incorrect date, slot, or student count, an invalid or unintended request could be presented to the lab in-charge. | **Yes.** Ground truth can be verified by comparing extracted fields directly against the original text in `requests.csv`. Python grounding assertions also verify numbers. | **System Developer (Student)** for prompt design, grounding rules, and validator assertions. |
| **Calendar & Semester Rules** (`check_date`) | **High.** If an impossible date (e.g., Feb 31) or a date outside the semester is permitted, booking schedules become invalid and disrupt classes. | **Yes.** Deterministically verified using Python `datetime` module and calendar math. Zero AI involved. | **System Developer (Student)** for correct date parsing logic. |
| **Sunday Closure Rule** (`decide` Rule 3) | **High.** If Sunday bookings are permitted, staff and security are unavailable, causing facility lockout. | **Yes.** Completely verifiable via Python `datetime.weekday() == 6`. Zero AI involved. | **System Developer (Student)** for calendar boundary check. |
| **Capacity Enforcement** (`decide` Rule 4) | **High.** Overcrowding causes severe safety violations, equipment shortage, and student disruption. | **Yes.** Completely verifiable by integer comparison (`students <= labs[lab].capacity`). Zero AI involved. | **System Developer (Student)** for math and data integrity. |
| **Collision & Conflict Detection** (`decide` Rule 5) | **Critical.** Double-booking causes two professors/classes to arrive simultaneously, creating classroom confrontation. | **Yes.** Completely verifiable by cross-referencing `(date, slot, lab)` tuples in memory and `bookings.csv`. | **System Developer (Student)** for collision detection logic. |
| **Final Booking Confirmation** (Master Register) | **Catastrophic.** Wrong entries in the permanent college timetable cause campus-wide scheduling chaos. | **Yes.** Verified through institutional authority and room log registers. | **Lab In-Charge (Human Checkpoint)**. |

---

## 2. The Human Checkpoint

> ### ⚠️ Mandatory Human Checkpoint
> **The lab in-charge must confirm every booking.**  
>
> 1. The software **NEVER** writes directly to `bookings.csv` or modifies existing confirmed records.
> 2. The software generates a **tentative schedule** (`schedule.csv`) and an **issues report** (`issues.csv`).
> 3. The **Lab In-Charge** inspects `schedule.csv`, performs physical/departmental sanity checks, and manually enters the approved requests into the master college booking register.
