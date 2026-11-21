# Internship Assessment Submission - Shaik [Your Surname]

## Candidate Information
- **Full Name:** Shaik [Your Surname]
- **Email Address:** [your email]
- **GitHub Profile URL:** https://github.com/[your-username]
- **LinkedIn Profile (Optional):** [your LinkedIn URL]
- **Submission Date:** [DD Month 2026]

---

## Task Deliverables

### Task 1: AI Document Assistant (RAG)
- **GitHub Repository URL:** https://github.com/[your-username]/[repo]/tree/main/task1-rag
- **Live Deployed Application URL:** [Streamlit URL for task1-rag]
- **Primary Technologies Used:** Python, Streamlit, pypdf, fastembed (BAAI/bge-small-en-v1.5), FAISS, Groq API (GPT-OSS 120B), pytest
- **Project Summary:**
  Users upload one or more PDFs, which are validated and extracted page by page with pypdf. Text is split with a custom recursive character splitter (900 characters, 150 overlap) that prefers paragraph, then sentence, then word boundaries. Each page is chunked separately so every chunk carries its document name, page number and chunk index.

  Chunks are embedded with BAAI/bge-small-en-v1.5 through fastembed (ONNX, no PyTorch) and stored in a FAISS inner-product index over normalised vectors, which is equivalent to cosine similarity. The index is rebuilt whenever a document is added, replaced or removed. At question time the query is embedded, the top 4 chunks above a 0.25 similarity threshold are retrieved, and they are sent to Groq with a system prompt that restricts the model to the numbered passages and requires a fixed refusal sentence when the answer is absent. If nothing passes the threshold the LLM is skipped entirely.

  The Streamlit interface shows chat history, inline citation markers and expandable source passages with file, page, chunk and similarity score. Scanned, empty, encrypted, corrupt, oversized and non-PDF files each produce a specific message and do not block other files in the batch.
- **Key Challenges & Solutions:**
  [Replace with your own experience. Points that apply to this build: keeping page numbers through chunking by splitting per page; avoiding a heavy PyTorch install by using fastembed; keeping the index consistent when documents change by rebuilding from per-document vectors; preventing hallucination by short-circuiting when retrieval finds nothing relevant.]

---

### Task 2: AI Agent with Tool Calling
- **GitHub Repository URL:** https://github.com/[your-username]/[repo]/tree/main/task2-agent
- **Live Deployed Application URL:** [Streamlit URL for task2-agent]
- **Primary Technologies Used:** Python, Streamlit, Groq native tool calling (GPT-OSS 120B), Open-Meteo API, Wikipedia API, Frankfurter API, pytest
- **Implemented Tools:**
  1. *calculator*: safe arithmetic evaluator built on an AST whitelist. Input: `expression` (string).
  2. *get_weather*: current conditions and 3-day forecast through Open-Meteo geocoding and forecast APIs. Inputs: `location` (string), `units` (celsius or fahrenheit).
  3. *search_wikipedia*: intro summary and link for the best matching article. Input: `query` (string).
  4. *convert_currency*: live exchange-rate conversion through Frankfurter. Inputs: `amount` (number), `from_currency`, `to_currency` (ISO codes).
- **Project Summary:**
  The agent uses the model's native function calling in a loop. Each turn sends the conversation history and the tool schemas, executes any requested tool calls (several per step are supported), feeds results back as tool messages, and repeats until the model produces a plain answer or a 5-round limit is reached, at which point tools are withheld to force a final reply. Greetings and general knowledge are answered directly without tools.

  A `ToolRegistry` validates arguments (required fields, types, enums, numeric strings), isolates tool exceptions, and returns error dictionaries that the model turns into friendly explanations. Network failures, rate limits, unknown places and unsupported currencies are handled explicitly. LLM failures are translated into user-friendly messages and the failed turn is rolled back from history. The UI shows every tool call with its arguments and result.
- **Key Challenges & Solutions:**
  [Replace with your own experience. Points that apply to this build: evaluating maths safely without eval; models sending numbers as strings, handled by coercion; preventing runaway tool loops with a step limit; keeping history valid for the API by never starting a trimmed window mid tool exchange.]

---

### Task 3: GitHub Repository AI Analyzer & Open-Source Contribution
- **GitHub Repository URL:** https://github.com/[your-username]/[repo]/tree/main/task3-github-analyzer
- **Live Deployed Application URL:** [Streamlit URL for task3-github-analyzer]
- **Primary Technologies Used:** Python, Streamlit, GitHub REST API, Groq API (JSON mode), pytest
- **Project Summary:**
  The analyzer accepts an owner/repo string or any common GitHub URL form, then fetches metadata, languages, README, the full recursive file tree, package descriptors and open good-first-issue and help-wanted issues from the GitHub REST API. It supports an optional personal access token and reports rate-limit, private or missing repository, empty repository, invalid token and network problems clearly.

  From the file tree it computes metrics: file and directory counts, extension breakdown, language percentages, presence of tests, CI, Docker, docs, linters, licence, contributing guide, changelog and code of conduct, and a deterministic 0 to 100 health score. The facts, a sample of the tree, the descriptors and the README are sent to Groq in JSON mode. The response is validated in code, requiring a summary and at least three complete recommendations, with one retry on malformed output. The dashboard presents the summary, tech stack, strengths, architecture patterns, prioritised recommendations, charts and contribution opportunities.
- **Open-Source Contribution:**
  - **Target Open-Source Repository:** [URL of the project you chose]
  - **Contribution URL (Issue / Pull Request):** [Direct link to your issue or PR]
  - **Contribution Summary:** [Describe the real problem you found, how you reproduced it or why it was needed, and what you submitted. See CONTRIBUTION-GUIDE.md.]
- **Key Challenges & Solutions:**
  [Replace with your own experience. Points that apply to this build: distinguishing rate-limit 403 responses from permission 403 responses; making LLM output reliable through JSON mode, tolerant parsing, validation and retry; working within unauthenticated API limits by using the recursive tree endpoint to avoid many calls.]

---

## AI Collaboration Disclosure

- **AI Tools Used:** Claude
- **How You Leveraged AI:** Drafting the initial project structure, modules, tests and documentation, then iterating on failures found by the test suites.
- **Verification & Ownership:**
  [Only keep this section if it is true. Describe what you personally ran, read and changed, for example: ran every test suite, ran each app locally against real APIs, deployed each app, read every module so you can explain it, and any refactoring you did.]

---

## Demonstration Video (Optional)
- **Video Link (Loom, YouTube unlisted, Google Drive):** [link]
