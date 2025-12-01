# app/ui/app.py
import streamlit as st
import requests
import time
import hashlib
from typing import List

BASE = "http://localhost:8000/healthbot"
SUGGEST_LIMIT = 8
TYPEAHEAD_DELAY = 0.25  # seconds (250 ms)


st.set_page_config(page_title="HealthBot Demo", layout="centered")


# -----------------------
# API helpers
# -----------------------
def api_post(path: str, params: dict = None, json_body: dict = None, timeout: int = 10):
    url = f"{BASE.rstrip('/')}/{path.lstrip('/')}"
    try:
        resp = requests.post(url, params=params, json=json_body, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        try:
            err = resp.json()
            if isinstance(err, dict):
                return {"error": err.get("detail") or err.get("error") or err}
        except Exception:
            pass
        return {"error": str(e)}


def get_suggestions_from_backend(query: str, limit: int = SUGGEST_LIMIT) -> List[str]:
    try:
        r = requests.get(f"{BASE}/suggest", params={"q": query, "limit": limit}, timeout=2)
        r.raise_for_status()
        j = r.json()
        return j.get("suggestions", []) if isinstance(j, dict) else []
    except Exception:
        return []


# -----------------------
# session state defaults
# -----------------------
defaults = {
    "session": None,
    "quiz": None,
    "last_eval": None,
    # canonical topic value (used to prefill widget when suggestion is applied)
    "topic_input_field": "",
    # actual widget key value (the live value of the text input)
    "topic_input_widget": None,
    "last_topic_value": "",
    "last_typed": 0.0,
    # flag used to apply suggestion safely on rerun
    "apply_suggestion": False,
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# When apply_suggestion is set, set the widget-key session_state BEFORE the widget is created.
# This avoids modifying the widget session_state after instantiation (Streamlit forbids that).
if st.session_state.apply_suggestion:
    st.session_state.topic_input_widget = st.session_state.topic_input_field
    st.session_state.apply_suggestion = False


# -----------------------
# start-session helper
# -----------------------
def start_session_callback():
    """
    This function is triggered via text_input on_change (Enter) or via Start button.
    It reads the widget value from st.session_state.topic_input_widget and calls the backend.
    """
    topic = (st.session_state.get("topic_input_widget") or "").strip()
    session_id = (st.session_state.get("session_id_input") or "").strip() or None
    if not topic:
        st.warning("Please enter a topic before submitting.")
        return

    with st.spinner("Starting session and fetching summary..."):
        res = api_post("start", json_body={"topic": topic, "session_id": session_id})
    if isinstance(res, dict) and res.get("error"):
        st.error(f"Failed to start session: {res['error']}")
    else:
        st.session_state.session = res
        st.session_state.quiz = None
        st.session_state.last_eval = None
        # keep canonical in sync
        st.session_state.topic_input_field = topic
        st.success("Session started")
        # rerun to show summary immediately
        st.rerun()


# -----------------------
# UI header
# -----------------------
st.title("🩺 HealthBot — Patient Education Demo")
st.caption("Search a health topic, get a summary, generate quizzes, and get evaluated feedback.")


# -----------------------
# Input + suggestions (no form)
# -----------------------
st.subheader("Start a Session")

# session id input (top-level, not inside a form)
if st.session_state.session:
    default_sid = st.session_state.session.get("session_id", "demo1")
else:
    default_sid = "demo1"
st.text_input("Session ID (optional)", key="session_id_input", value=default_sid)

# Text input for topic — uses widget key 'topic_input_widget'
# on_change triggers start_session_callback when Enter is pressed by user
st.text_input(
    "Enter a health topic",
    value=(st.session_state.topic_input_widget or ""),
    placeholder="Type at least 2 letters (e.g., 'ocd', 'diab') and press Enter or click Start",
    key="topic_input_widget",
    on_change=start_session_callback,
)

# track typing times to implement typeahead pause detection
typed_value = st.session_state.get("topic_input_widget") or ""
if typed_value != st.session_state.get("last_topic_value"):
    st.session_state.last_topic_value = typed_value
    st.session_state.last_typed = time.time()

suggestions = []
if len(typed_value.strip()) >= 2 and (time.time() - st.session_state.last_typed) > TYPEAHEAD_DELAY:
    suggestions = get_suggestions_from_backend(typed_value.strip())

# Render suggestions under the input (Google-like)
if suggestions:
    st.markdown("##### Suggestions")
    cols = st.columns(1)
    for s in suggestions:
        # stable key
        key_hash = hashlib.md5(s.encode("utf-8")).hexdigest()[:8]
        btn_key = f"suggest_{key_hash}"
        # Buttons are allowed here because we're not inside a form
        if st.button(s, key=btn_key):
            # Set canonical value, set apply flag so widget is updated safely on rerun
            st.session_state.topic_input_field = s
            st.session_state.apply_suggestion = True
            # Rerun so widget gets its value prefilled
            st.rerun()

# Start button (click to start session)
if st.button("Start Session"):
    # when clicked, call the same function
    start_session_callback()


# -----------------------
# Summary display
# -----------------------
if st.session_state.session and st.session_state.session.get("summary"):
    st.subheader("Patient-friendly Summary")
    st.write(st.session_state.session.get("summary"))


# -----------------------
# Generate quiz
# -----------------------
if st.session_state.session:
    if st.button("Generate Quiz"):
        sid = st.session_state.session.get("session_id")
        if not sid:
            st.error("Session missing session_id. Restart session.")
        else:
            with st.spinner("Generating quiz..."):
                res = api_post("quiz", params={"session_id": sid})
            if isinstance(res, dict) and res.get("error"):
                st.error(f"Failed to generate quiz: {res['error']}")
            else:
                quiz = res.get("quiz")
                if not quiz:
                    st.error("No quiz returned from server.")
                else:
                    # normalize options
                    opts = quiz.get("options")
                    quiz["options"] = opts if opts else None
                    st.session_state.quiz = quiz
                    st.session_state.last_eval = None
                    st.success("Quiz generated")


# -----------------------
# Quiz + submit
# -----------------------
if st.session_state.quiz:
    st.subheader("Quiz")
    st.markdown(f"**Question:** {st.session_state.quiz.get('question')}")
    show_hint = st.checkbox("Show hint")
    if show_hint and st.session_state.quiz.get("hint"):
        st.info(st.session_state.quiz.get("hint"))

    opts = st.session_state.quiz.get("options")

    if opts:
        choice = st.radio("Select an option:", opts, key="mcq_choice")
        if st.button("Submit Answer"):
            payload = {"answer": choice, "session_id": st.session_state.session.get("session_id")}
            with st.spinner("Evaluating..."):
                res = api_post("answer", json_body=payload)
            if isinstance(res, dict) and res.get("error"):
                st.error(res["error"])
            else:
                st.session_state.last_eval = res.get("evaluation", res)
                st.success("Answer evaluated")
    else:
        short_answer = st.text_input("Your answer", key="short_answer_input", placeholder="Type and press Enter to submit")
        # Enter in this short_answer will not auto-submit by default; provide a button for clarity:
        if st.button("Submit Answer"):
            if not short_answer or not short_answer.strip():
                st.warning("Please enter an answer.")
            else:
                payload = {"answer": short_answer, "session_id": st.session_state.session.get("session_id")}
                with st.spinner("Evaluating..."):
                    res = api_post("answer", json_body=payload)
                if isinstance(res, dict) and res.get("error"):
                    st.error(res["error"])
                else:
                    st.session_state.last_eval = res.get("evaluation", res)
                    st.success("Answer evaluated")


# -----------------------
# Evaluation display
# -----------------------
if st.session_state.last_eval:
    ev = st.session_state.last_eval
    st.subheader("Evaluation")
    verdict = ev.get("verdict", "")
    score = ev.get("score")
    if verdict == "correct":
        st.success(f"Correct — Score: {score if score is not None else '—'}")
    elif verdict == "partial":
        st.warning(f"Partial — Score: {score if score is not None else '—'}")
    else:
        st.error(f"Incorrect — Score: {score if score is not None else '—'}")

    st.write("**Explanation**")
    st.write(ev.get("explanation", "No explanation provided."))
    if ev.get("citations"):
        with st.expander("Citations"):
            for c in ev["citations"]:
                st.markdown(f"- {c}")


# -----------------------
# Clear session
# -----------------------
if st.session_state.session:
    if st.button("Clear Session"):
        sid = st.session_state.session.get("session_id")
        with st.spinner("Clearing session..."):
            api_post("clear", params={"session_id": sid})
        st.session_state.session = None
        st.session_state.quiz = None
        st.session_state.last_eval = None
        st.session_state.topic_input_field = ""
        st.session_state.topic_input_widget = ""
        st.success("Session cleared")
        st.rerun()
