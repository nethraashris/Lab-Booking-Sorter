# Student Project Reflection
**Course:** CIT AI-Native Engineering Programme · Semester 1 · Assessment 5  
**Project:** Lab Booking Request Sorter  
**Word Count:** ~410 words  

Building the Lab Booking Request Sorter taught me the critical difference between using Artificial Intelligence for natural language understanding and relying on deterministic code for decision-making. Before this capstone project, I assumed an advanced Large Language Model could handle the entire lab booking workflow on its own, including checking room capacity and preventing double bookings. However, as I designed the architecture and tested edge cases, I quickly realized that language models are probabilistic text predictors rather than reliable rule engines.

The most valuable design insight I gained was strictly enforcing a clear boundary between the LLM and Python. By restricting the Groq LLM to information extraction using the 5-role framework, the model had only one focused responsibility: converting messy human requests into structured JSON. I then used standard Python functions with `datetime` and integer comparisons to enforce business logic: verifying whether a date is a real calendar day, ensuring the lab is not closed on Sundays, checking headcounts against laboratory capacity, and detecting clashes with previous bookings.

During our red-team testing, this architecture proved its strength. When a request contained an impossible date like "31 February" or relative phrasing like "tomorrow", our Python fact-checking function intercepted the error immediately and marked it as `needs_more_info`. Even when I tested an adversarial prompt injection trying to force the system to mark a room as "approved", the system remained safe because Python never delegates the status decision to the AI.

Equally important was establishing the human checkpoint. In campus facility management, errors carry real human consequences: double-booking a lab leaves students standing outside, while exceeding capacity creates safety hazards. By ensuring the software only produces a tentative schedule (`schedule.csv`) and never directly modifies the official `bookings.csv` register, the lab in-charge retains complete authority over all confirmations.

Working on this project has significantly strengthened my programming fundamentals. I learned how to use Python dictionaries, sets, CSV file handling, environment variables for API key security, and structured unit testing. Most of all, it demonstrated how to build responsible AI software that enhances human workflows without removing human accountability.

---
*(Note for faculty review: [Insert personal reflections regarding your experience running test requests during the showcase presentation here if desired])*
