# Cost and Latency Note
**Project:** Lab Booking Request Sorter  
**Course:** CIT AI-Native Engineering Programme · Capstone Project  
**LLM Provider:** Groq Cloud API  
**Default Model:** `llama-3.3-70b-versatile` (or `llama-3.1-8b-instant`)

---

## 1. Workload Assumptions

| Metric | Estimated Value | Notes |
| :--- | :--- | :--- |
| **Incoming Requests per Day** | 25 requests | Typical college department / club daily booking volume |
| **Input Tokens per Request** | ~350 tokens | System prompt (~280 tokens) + User request text (~30-70 tokens) |
| **Output Tokens per Request** | ~60 tokens | Structured JSON response (5 fields) |
| **Validation Failure / Retry Rate** | ~5% (1 in 20 requests) | Well-crafted 5-role system prompt ensures very low retry frequency |
| **Total API Calls per Day** | ~26 to 28 calls | 25 base calls + ~1 to 3 retries |

---

## 2. Latency Analysis

- **Average API Response Time (Groq LPU):** ~0.25 to 0.45 seconds per request.
- **Python Processing Time per Request:** < 0.002 seconds (calendar check, capacity comparison, conflict lookup).
- **Total Batch Execution Time (25 requests):**  
  $$25 \times 0.35\text{ s} \approx 8.75\text{ seconds}$$
- **Impact of Retries:**  
  A retried request adds one additional network roundtrip (~0.35 s), meaning a retried request completes in ~0.70 s total. Because calls run sequentially in console mode, retries have negligible impact on user wait time.

---

## 3. Cost Analysis (Groq API Pricing)

Groq pricing for `llama-3.3-70b-versatile`:
- **Input Pricing:** \$0.59 per 1,000,000 tokens
- **Output Pricing:** \$0.79 per 1,000,000 tokens

*(Note: Groq currently offers generous free tier credits for students and developers, meaning testing and showcase runs are **\$0.00 / completely free** during development).*

### Daily Cost Calculation (Pay-as-you-go calculation)
For 28 total calls (including retries):
- **Total Daily Input Tokens:** $28 \times 350 = 9,800\text{ tokens}$
- **Total Daily Output Tokens:** $28 \times 60 = 1,680\text{ tokens}$

$$\text{Daily Input Cost} = \frac{9,800}{1,000,000} \times \$0.59 \approx \$0.00578$$
$$\text{Daily Output Cost} = \frac{1,680}{1,000,000} \times \$0.79 \approx \$0.00133$$
$$\mathbf{\text{Total Cost per Day}} = \$0.00578 + \$0.00133 \approx \mathbf{\$0.0071} \text{ (Less than 1 cent USD per day)}$$

### Monthly Cost (22 Working Days)
$$\mathbf{\text{Monthly Operating Cost}} \approx 22 \times \$0.0071 \approx \mathbf{\$0.16}\text{ / month}$$

---

## 4. How to Update with Your Actual Figures
To recalculate for your faculty submission:
1. Check your Groq console dashboard at [https://console.groq.com](https://console.groq.com) under **Usage**.
2. Replace the token counts and pricing with the exact figures from your API billing tab.
3. If using `llama-3.1-8b-instant` (\$0.05 / 1M input tokens), the daily cost drops to **\$0.0006 per day**.
