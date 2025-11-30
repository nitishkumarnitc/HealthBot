# ui/app.py
import streamlit as st
import requests

BASE = "http://localhost:8000/healthbot"

st.set_page_config(page_title="HealthBot Demo", layout="centered")


# Utilities
def api_post(path, params=None, json=None):
    url = f"{BASE}/{path}"
    try:
        r = requests.post(url, params=params, json=json)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        try:
            return r.json()
        except:
            return {"error": str(e)}


if "session" not in st.session_state:
    st.session_state.session = None
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "last_eval" not in st.session_state:
    st.session_state.last_eval = None

# ------------------------------
# Title
# ------------------------------
st.title("🩺 HealthBot — Patient Education Demo")

# ================================================
# 1. TOPIC + START SESSION (ENTER submits form)
# ================================================
st.subheader("Start a Session")

with st.form("start_session_form"):
    topic = st.text_input("Enter a health topic", placeholder="e.g., OCD, diabetes, asthma")
    session_id = st.text_input("Session ID", value="demo1")
    start_clicked = st.form_submit_button("Start Session")

    if start_clicked:
        if not topic.strip():
            st.error("Please enter a topic.")
        else:
            res = api_post("start", json={"topic": topic, "session_id": session_id})
            st.session_state.session = res
            st.session_state.quiz = None
            st.session_state.last_eval = None
            st.success("Session started!")

# ------------------------------
# Show summary if available
# ------------------------------
if st.session_state.session and st.session_state.session.get("summary"):
    st.subheader("Patient-friendly Summary")
    st.write(st.session_state.session["summary"])

# ================================================
# 2. GENERATE QUIZ
# ================================================
if st.session_state.session:
    if st.button("Generate Quiz"):
        res = api_post("quiz", params={"session_id": st.session_state.session["session_id"]})
        st.session_state.quiz = res.get("quiz")
        st.session_state.last_eval = None

# ================================================
# 3. QUIZ + SUBMIT (ENTER submits answer)
# ================================================
if st.session_state.quiz:
    st.subheader("Quiz")
    q = st.session_state.quiz.get("question")
    st.write(f"**Question:** {q}")

    # If options exist → MCQ mode
    options = st.session_state.quiz.get("options")

    with st.form("answer_form"):
        if options:
            answer = st.radio("Select an option:", options)
        else:
            answer = st.text_input("Your answer", placeholder="Type here and hit Enter")

        submit_clicked = st.form_submit_button("Submit Answer")

        if submit_clicked:
            payload = {
                "answer": answer,
                "session_id": st.session_state.session["session_id"]
            }
            res = api_post("answer", json=payload)
            st.session_state.last_eval = res.get("evaluation", res)
            st.success("Answer submitted!")

# ================================================
# 4. SHOW EVALUATION
# ================================================
if st.session_state.last_eval:
    ev = st.session_state.last_eval
    st.subheader("Evaluation Result")

    st.write(f"**Verdict:** {ev.get('verdict', '').capitalize()}")
    if ev.get("score") is not None:
        st.write(f"**Score:** {ev['score']:.2f}")

    st.write("**Explanation:**")
    st.write(ev.get("explanation", "No explanation provided."))

    if ev.get("citations"):
        st.write("**Citations:**")
        for c in ev["citations"]:
            st.markdown(f"- {c}")

# ================================================
# 5. CLEAR SESSION
# ================================================
if st.session_state.session:
    if st.button("Clear Session"):
        api_post("clear", params={"session_id": st.session_state.session["session_id"]})
        st.session_state.session = None
        st.session_state.quiz = None
        st.session_state.last_eval = None
        st.info("Session cleared.")
