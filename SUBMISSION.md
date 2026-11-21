# Internship Assessment Submission - Shaik Samiulla

## Candidate Information
- **Full Name:** Shaik Samiulla
- **Email Address:** smssamiulla4@gmail.com
- **GitHub Profile URL:** https://github.com/Shaik-Sam
- **LinkedIn Profile (Optional):** [your LinkedIn URL]
- **Submission Date:** 21 November 2026

---

## Task Deliverables

### Task 1: AI Document Assistant (RAG)
- **GitHub Repository URL:** https://github.com/Shaik-Sam/ghanex-assessment/tree/main/task1-rag
- **Live Deployed Application URL:** https://task1-pdf-assistant.streamlit.app/
- **Primary Technologies Used:** Python, Streamlit, pypdf, fastembed (BAAI/bge-small-en-v1.5), FAISS, Groq API (openai/gpt-oss-120b), pytest
- **Project Summary:**
  Users upload one or more PDFs, which are validated and extracted page by page with pypdf. Text is split with a custom recursive character splitter (900 characters, 150 overlap) that prefers paragraph, then sentence, then word boundaries. Each page is chunked separately so every chunk carries its document name, page number and chunk index.

  Chunks are embedded with BAAI/bge-small-en-v1.5 through fastembed (ONNX, no PyTorch) and stored in a FAISS inner-product index over normalised vectors, which is equivalent to cosine similarity. The index is rebuilt whenever a document is added, replaced or removed. At question time the query is embedded, the top 4 chunks above a 0.25 similarity threshold are retrieved, and they are sent to Groq with a system prompt that restricts the model to the numbered passages and requires a fixed refusal sentence when the answer is absent. If nothing passes the threshold the LLM is skipped entirely.

  The Streamlit interface shows chat history, inline citation markers and expandable source passages with file, page, chunk and similarity score. Scanned, empty, encrypted, corrupt, oversized and non-PDF files each produce a specific message and do not block other files in the batch.
- **Key Challenges & Solutions:**
  The first run of the app failed with an HTTP 404 from the language model API. The model name I had configured had been retired by Groq on 16 August 2026, which I confirmed in Groq's deprecation notice. I switched to openai/gpt-oss-120b, kept the model name configurable through the GROQ_MODEL variable, made the app show an actionable message on a 404 instead of a bare status code, and raised the output token limit because reasoning models spend part of that limit on internal reasoning.

  A second issue was that my terminal and my .env file disagreed about configuration. The sidebar showed an old model name that came from outside the code. I traced it by checking environment variables, which take priority over .env values, and I now check both when configuration looks wrong.

  On the design side, keeping page numbers meant chunking each page separately instead of the whole document. I avoided a heavy PyTorch install by using fastembed with ONNX Runtime, which also helps the app fit free hosting. To keep retrieval correct when files change, the vector store keeps vectors per document and rebuilds the FAISS index on every add, replace or remove.

---

### Task 2: AI Agent with Tool Calling
- **GitHub Repository URL:** https://github.com/Shaik-Sam/ghanex-assessment/tree/main/task2-agent
- **Live Deployed Application URL:** https://task2-ai-agent.streamlit.app/
- **Primary Technologies Used:** Python, Streamlit, Groq native tool calling (openai/gpt-oss-120b), Open-Meteo API, Wikipedia API, Frankfurter API, pytest
- **Implemented Tools:**
  1. *calculator*: safe arithmetic evaluator built on an AST whitelist. Input: `expression` (string).
  2. *get_weather*: current conditions and 3-day forecast through Open-Meteo geocoding and forecast APIs. Inputs: `location` (string), `units` (celsius or fahrenheit).
  3. *search_wikipedia*: intro summary and link for the best matching article. Input: `query` (string).
  4. *convert_currency*: live exchange-rate conversion through Frankfurter. Inputs: `amount` (number), `from_currency`, `to_currency` (ISO codes).
- **Project Summary:**
  The agent uses the model's native function calling in a loop. Each turn sends the conversation history and the tool schemas, executes any requested tool calls (several per step are supported), feeds results back as tool messages, and repeats until the model produces a plain answer or a 5-round limit is reached, at which point tools are withheld to force a final reply. Greetings and general knowledge are answered directly without tools.

  A `ToolRegistry` validates arguments (required fields, types, enums, numeric strings), isolates tool exceptions, and returns error dictionaries that the model turns into friendly explanations. Network failures, rate limits, unknown places and unsupported currencies are handled explicitly. LLM failures are translated into user-friendly messages and the failed turn is rolled back from history. The UI shows every tool call with its arguments and result.
- **Key Challenges & Solutions:**
  The calculator needed to evaluate arbitrary maths without using eval, which would let a model or user run code. I parse the expression into an AST and only allow a whitelist of numeric operators, constants and math functions, and I also limit expression length and exponent size. Language models sometimes pass numbers as strings such as "1,000", so the registry coerces numeric strings before validation.

  To stop runaway tool loops the agent has a five-round limit, after which tools are withheld and the model must answer. When a tool fails, it returns an error object instead of raising, so the model can explain the problem to the user. I also had to make sure the trimmed conversation history never starts in the middle of a tool exchange, because the API rejects tool messages without their matching call. The same retired-model 404 from Task 1 affected this app, and it now gets the same clear error message.

---

### Task 3: GitHub Repository AI Analyzer & Open-Source Contribution
- **GitHub Repository URL:** https://github.com/Shaik-Sam/ghanex-assessment/tree/main/task3-github-analyzer
- **Live Deployed Application URL:** https://task3-repo-analyzer.streamlit.app/
- **Primary Technologies Used:** Python, Streamlit, GitHub REST API, Groq API (JSON mode), pytest
- **Project Summary:**
  The analyzer accepts an owner/repo string or any common GitHub URL form, then fetches metadata, languages, README, the full recursive file tree, package descriptors and open good-first-issue and help-wanted issues from the GitHub REST API. It supports an optional personal access token and reports rate-limit, private or missing repository, empty repository, invalid token and network problems clearly.

  From the file tree it computes metrics: file and directory counts, extension breakdown, language percentages, presence of tests, CI, Docker, docs, linters, licence, contributing guide, changelog and code of conduct, and a deterministic 0 to 100 health score. The facts, a sample of the tree, the descriptors and the README are sent to Groq in JSON mode. The response is validated in code, requiring a summary and at least three complete recommendations, with one retry on malformed output. The dashboard presents the summary, tech stack, strengths, architecture patterns, prioritised recommendations, charts and contribution opportunities.
- **Open-Source Contribution:**
  - **Target Open-Source Repository:** [URL of the open-source project]
  - **Contribution URL (Issue / Pull Request):** [Direct link to your issue or PR]
  - **Contribution Summary:** [Explain the issue you identified, why it matters, and what you submitted]
- **Key Challenges & Solutions:**
  During testing the app reported that the GitHub token was rejected, even though a direct API call with the token from my .env file returned HTTP 200. That showed the token was valid and that the app was sending a different value, so the problem was in how the app chose its token. I redesigned the sidebar field as an optional override that starts empty, made the app use the GITHUB_TOKEN from the environment by default, added a caption showing which token source is in use, and added a fallback that retries without a token and shows a warning if GitHub rejects it.

  GitHub returns status 403 for both rate limiting and permission errors, so the client checks the rate-limit headers and the message text to tell them apart and shows the reset time for rate limits. Unauthenticated requests are limited to 60 per hour, so I used the recursive git tree endpoint to read the whole file structure in one request. To make the language model output reliable I use JSON mode, tolerant JSON extraction, strict validation of the fields, normalisation of priorities and categories, and one retry on malformed output.


