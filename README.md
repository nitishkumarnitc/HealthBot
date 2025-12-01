# 🩺 **HealthBot — Patient Education & Quiz Assistant**

HealthBot is an AI-powered medical education assistant built with **FastAPI**, **LangChain/LangGraph**, **OpenAI**, and a **Streamlit UI**.
It helps users:

* Search a health topic
* Get a simple, patient-friendly summary
* Generate comprehension quizzes
* Evaluate answers with explanations and citations
* Interact using a clean UI with **Google-style typeahead suggestions**

This project serves as a **foundation** for building clinical education tools, patient-support systems, and AI-driven health conversation agents.

---

## 🚀 **Tech Stack**

### **Backend**

* FastAPI
* LangChain + LangGraph
* OpenAI LLMs (via async calls)
* Redis (session store)
* Tavily (search augmentation)

### **Frontend**

* Streamlit
* Custom typeahead (non-native autocomplete)
* UX optimized for fast medical search

### **Data**

* 700+ predefined medical terms for autosuggestions
* Live search via backend API (`/suggest?q=`)

---

## 📦 **Installation**

Clone the repo:

```bash
git clone https://github.com/<your-username>/HealthBot.git
cd HealthBot
```

Create virtual environment & install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Add environment variables:

```
OPENAI_API_KEY=your_key
TAVILY_API_KEY=your_key
REDIS_URL=redis://localhost:6379
```

---

## ▶️ **Running the Backend**

From project root:

```bash
uvicorn app.main:app --reload
```

Backend will start at:

👉 [http://localhost:8000](http://localhost:8000)

---

## ▶️ **Running the Frontend (Streamlit)**

```bash
streamlit run app/ui/app.py
```

UI will start at:

👉 [http://localhost:8501](http://localhost:8501)

---

# 🧠 **How It Works**

### **1. Start Session**

* User enters a health topic
* Backend:

  * Validates topic
  * Fetches search results (Tavily)
  * Summarizes using OpenAI
  * Saves session in Redis

### **2. Quiz Generation**

* LLM generates:

  * 1 clear comprehension question
  * short-answer or MCQ
  * hint
  * canonical answer (not shown to user)

### **3. Answer Evaluation**

* User enters an answer
* LLM:

  * Scores (0–1)
  * Gives verdict (“correct”, “partial”, “incorrect”)
  * Provides explanation
  * Provides citations from summary

### **4. Session Reset**

Clean up Redis state and restart fresh.

---

# 🧰 **Project Structure**

```
app/
 ├── main.py                # FastAPI app entry
 ├── core/
 │    ├── prompts.py        # LLM prompts in one place
 │    ├── workflow.py       # LangGraph-style workflow
 │    └── llm.py            # OpenAI client setup
 ├── routes/
 │    └── healthbot.py      # API routes
 ├── services/
 │    ├── search_service.py
 │    ├── summary_service.py
 │    └── quiz_service.py
 └── utils/
      └── state.py          # Redis session helpers
ui/
 └── app.py                  # Streamlit UI
```

---

# 🛠 **How to Make This Better (Next Enhancements)**

### ✅ 1. **More Accurate Medical Summaries**

* Use **MedLM**, **PubMedBERT**, or **BioGPT** models
* Add retrieval-augmented generation (RAG) from medical databases
* Enforce stricter medical disclaimers

### ✅ 2. **Improved Quiz Generation**

* Support multi-question quizzes
* Difficulty levels
* Adaptive quiz based on previous score

### ✅ 3. **Realtime Streaming**

* Use OpenAI stream endpoint
* Show summary word-by-word in UI
* Show evaluation streaming

### ✅ 4. **Better UI/UX**

* Replace Streamlit with:

  * Next.js + Tailwind
  * React + ShadCN
  * SvelteKit
* Add animations + chat UI

### ✅ 5. **Analytics Dashboard**

* Track:

  * Topics searched
  * User responses
  * Avg score
  * Most misunderstood topics

### ✅ 6. **User Authentication**

* JWT-based accounts
* Save past learning sessions
* Provide weekly learning reports

### ✅ 7. **Doctor Mode / Expert Mode**

* Higher-density summary
* Include citations
* Add differential diagnosis outline (non-clinical, informational only)

### ✅ 8. **Multilingual Support**

* Hindi, Bengali, Tamil, Odia, etc.
* Automatic translation with medical terminology safety checks

### ✅ 9. **Voice Input + Voice Output**

* Whisper for input
* TTS for reading summaries aloud

### ✅ 10. **Deployments**

* Docker Compose
* AWS ECS / Lambda
* Render / Railway

---

# 🔮 **Future Scope: Turning HealthBot Into a Product**

### ✔️ Symptom → Education Flow

User enters a symptom → Bot teaches probable causes (without diagnosis).

### ✔️ Treatment Understanding Assistant

Explain treatment plans and medications in simple language.

### ✔️ Hospital/Clinic Integration

Doctors send patient education summaries automatically.

### ✔️ School/College Health Education

A self-paced quiz-based learning system.

### ✔️ Insurance / Telemedicine Add-On

"Explain my medical report" feature.

### ✔️ AI Health Coach (non-clinical)

Helps users form habits:

* Sleep
* Nutrition
* Stress
* Exercise

---

# 🤝 Contributing

Pull Requests are welcome!

---

# 📄 License

MIT License — open and free to use.

