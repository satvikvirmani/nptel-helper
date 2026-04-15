import streamlit as st
import json
import random
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try to import google genai
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

st.set_page_config(page_title="NPTEL Quiz App", layout="wide")

def load_data():
    questions = []
    # Load primary data source
    if os.path.exists("ai_for_management.json"):
        with open("ai_for_management.json", "r") as f:
            try:
                data = json.load(f)
                if isinstance(data, dict):
                    # Flatten data and inject heading into the questions
                    for heading, qs in data.items():
                        for q in qs:
                            q['heading'] = heading
                            questions.append(q)
                elif isinstance(data, list):
                    questions = data
            except:
                pass
    
    # Fallback to older format if ai_for_management is empty
    if not questions and os.path.exists("questions.json"):
        with open("questions.json", "r") as f:
            try:
                questions = json.load(f)
            except:
                pass
                
    return questions

def main():
    st.title("NPTEL Learning & Quiz App")

    # Initialize session state variables
    if "questions" not in st.session_state:
        st.session_state.questions = load_data()
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {}
    if "llm_explanation" not in st.session_state:
        st.session_state.llm_explanation = {}

    questions = st.session_state.questions

    with st.sidebar:
        st.header("Settings")
        api_key = os.environ.get("GEMINI_API_KEY", "")
        
        if st.button("Shuffle Questions"):
            random.shuffle(st.session_state.questions)
            st.session_state.user_answers = {}
            st.session_state.llm_explanation = {}
            st.rerun()
            
        st.button("Reload Database", on_click=lambda: st.session_state.update(
            {"questions": load_data(), "user_answers": {}, "llm_explanation": {}}
        ))
            
        st.write("---")
        if questions:
            st.write(f"Total Questions: {len(questions)}")

    if not questions:
        st.warning("No questions found! Please run the scraper.py first to generate ai_for_management.json.")
        st.info("Example: python scraper.py https://onlinecourses.nptel.ac.in/noc...")
        return

    # Main area - Render all questions at once
    for idx, q in enumerate(questions):
        st.write("---")
        
        if 'heading' in q:
            st.caption(f"Assessment: {q['heading']}")
            
        st.markdown(f"**Question {idx + 1}: {q['question']}**")
        
        # User choice
        choices = q.get("choices", [])
        correct_ans = q.get("answer", [])
        
        # Ensure correct_ans is a list
        if isinstance(correct_ans, str):
            correct_ans = [correct_ans]
            
        is_multiple = len(correct_ans) > 1

        if choices:
            selected_choices = st.session_state.user_answers.get(idx, [])
            if isinstance(selected_choices, str):
                selected_choices = [selected_choices]
                
            current_selection = []
            
            if is_multiple:
                st.markdown("*(Multiple correct options are possible)*")
                for c in choices:
                    is_checked = c in selected_choices
                    if st.checkbox(c, value=is_checked, key=f"chk_{idx}_{choices.index(c)}"):
                        current_selection.append(c)
            else:
                default_idx = None
                if selected_choices and selected_choices[0] in choices:
                    default_idx = choices.index(selected_choices[0])
                ans = st.radio(f"Select your answer for Question {idx + 1}:", choices, index=default_idx, key=f"radio_{idx}", label_visibility="collapsed")
                if ans:
                    current_selection.append(ans)
            
            # Action Buttons Row
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("Submit Answer", key=f"submit_{idx}", type="primary"):
                    if current_selection:
                        st.session_state.user_answers[idx] = current_selection
                        st.rerun()
                    else:
                        st.warning("Please select an option first.")
            with col2:
                # LLM integration
                if st.button("Learn more via LLM", key=f"llm_{idx}"):
                    if not api_key:
                        st.error("Please enter a Gemini API Key in the sidebar first.")
                    elif not GENAI_AVAILABLE:
                        st.error("Google GenAI SDK is not installed. Make sure to pip install google-genai.")
                    else:
                        with st.spinner("Analyzing question and generating explanation..."):
                            import time
                            max_retries = 4
                            curr_wait = 2
                            
                            for attempt in range(max_retries):
                                try:
                                    client = genai.Client(api_key=api_key)
                                    correct_str = " AND ".join(correct_ans)
                                    prompt = f"""
                                    I am studying for an exam. 
                                    
                                    Here is the question:
                                    "{q['question']}"
                                    
                                    The correct answer is: "{correct_str}"
                                    
                                    Please explain why this is the correct answer and break down the underlying core concepts. Keep the explanation concise, educational, and easy to understand.
                                    """
                                    response = client.models.generate_content(
                                        model='gemini-3.1-flash-lite-preview',
                                        contents=prompt
                                    )
                                    st.session_state.llm_explanation[idx] = response.text
                                    break
                                except Exception as e:
                                    err_str = str(e)
                                    # Retry on 503 or Unavailable errors
                                    if ("503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str) and attempt < max_retries - 1:
                                        st.warning(f"Server is busy, retrying in {curr_wait} seconds... (Attempt {attempt+1}/{max_retries})")
                                        time.sleep(curr_wait)
                                        curr_wait *= 2
                                    else:
                                        st.error(f"Error calling API after {attempt+1} attempt(s): {err_str}")
                                        break

        # Show feedback and LLM explanation if applicable
        if idx in st.session_state.user_answers:
            user_ans = st.session_state.user_answers[idx]
            
            st.write("")
            # Compare sets to ignore order
            if set(user_ans) == set(correct_ans):
                st.success("Correct!")
            else:
                st.error("Incorrect.")
                
            correct_str = " AND ".join(correct_ans)
            st.info(f"**Accepted Answer:** {correct_str}")
            
        if idx in st.session_state.llm_explanation:
            st.info("### AI Tutor Explanation:")
            st.markdown(st.session_state.llm_explanation[idx])

if __name__ == "__main__":
    main()
