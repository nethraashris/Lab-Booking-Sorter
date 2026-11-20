# AI Decision Journal
**Project:** Lab Booking Request Sorter  
**Student Author:** First-Year AI Engineering Student  
**Course:** CIT AI-Native Engineering Programme · Assessment 5  

---

### Decision 1: Boundary Separation Between AI and Python
- **What AI Suggested:** The AI initially proposed letting the LLM read `bookings.csv` and directly decide the status (e.g. outputting `"status": "available"` or `"status": "conflict"` directly in the JSON).
- **What I Decided / Changed:** **Rejected the suggestion.** I strictly enforced that the LLM must **only extract facts** (`lab`, `date`, `slot`, `students`, `summary`). Python code must make all status decisions.
- **Why:** LLMs can hallucinate dates, cannot accurately perform integer comparisons like `55 > 60` in complex scenarios, and cannot reliably keep in-memory track of state collisions across a batch of 20 requests. Python is deterministic and 100% auditable.

---

### Decision 2: Handling Relative Dates ("Tomorrow", "Next Friday")
- **What AI Suggested:** Have the LLM read the request's `sent` date and calculate "tomorrow" by adding one day.
- **What I Decided / Changed:** **Changed the design.** I instructed the LLM and the Python grounding checker to reject relative dates and output `date: null`.
- **Why:** In academic settings, faculty send forwarded emails or notes days after drafting them. Allowing an LLM to guess "tomorrow" leads to catastrophic booking misunderstandings. Forcing explicit calendar dates protects lab operations and routes ambiguous requests to `needs_more_info`.

---

### Decision 3: API Provider Choice (Groq Cloud)
- **What AI Suggested:** Use generic commercial APIs or local heavyweight models.
- **What I Decided / Changed:** **Adopted Groq API (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`).**
- **Why:** Groq provides ultra-fast inference speeds (sub-second responses), excellent native JSON mode support (`response_format={"type": "json_object"}`), and a free tier tier that avoids student costs.

---

### Decision 4: Safe Offline Rule-Based Fallback
- **What AI Suggested:** Raise an unhandled exception or stop execution if the API key is missing or network disconnects.
- **What I Decided / Changed:** **Implemented a safe regex fallback function (`fallback_extraction`).**
- **Why:** If the internet drops during the live showcase or if the Groq rate limit is hit, the program degrades gracefully rather than crashing in front of examiners.

---

### Decision 5: Read-Only Invariance on `bookings.csv`
- **What AI Suggested:** Automatically append approved requests to `bookings.csv`.
- **What I Decided / Changed:** **Strictly prohibited writing to `bookings.csv`.** The program only produces `schedule.csv`.
- **Why:** Compliance with the project requirement and real-world safety: only the authorized human Lab In-Charge can make permanent changes to the college facility register.
