import json
import streamlit as st
from collections import deque

from shared import log_message as logr
import gennie_core

# Initialize the deque to store the latest 5 interactions
interactions = deque(maxlen=5)

def main():
    st.title('Gennie Answer Engine')
    with st.sidebar:
        st.title("Options")
        # Model selection
        model_id = st.selectbox("LLM Model", ['gemini-1.5-flash-001', 'gemini-1.5-pro-001', 'claude-3-5-sonnet-20240620', 'claude-3-opus-20240229'])
        num_google_search_results = st.slider('Num Results:', 1, 10, step=1, value=5)

        # New date reference selection
        date_reference = st.selectbox('Date Reference', ['d', 'w', 'm', 'y'], format_func=lambda x: {'d': 'Days', 'w': 'Weeks', 'm': 'Months', 'y': 'Years'}[x], index=3)

        # Adjust slider label and range based on date reference
        if date_reference == 'd':
            results_max_age = st.slider('Search Max Age', 1, 30, step=1, value=7)
        elif date_reference == 'w':
            results_max_age = st.slider('Search Max Age', 1, 52, step=1, value=4)
        elif date_reference == 'm':
            results_max_age = st.slider('Search Max Age', 1, 12, step=1, value=6)
        else:  # years
            results_max_age = st.slider('Search Max Age', 1, 10, step=1, value=3)

        # Combine date_reference and results_max_age
        date_restrict = f"{date_reference}{results_max_age}"
        
        # Add checkbox for including history
        include_history = st.checkbox("Include History")
        
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Logic for Uploading image
    if 'history' not in st.session_state:
        st.session_state.history = deque(maxlen=5)
        
    if prompt := st.chat_input("What is up?"):
        with st.spinner('Processing response...'):
            # Reset pagination for new question
            user_message = {"role": "user", "content": prompt}
            st.session_state.messages.append(user_message)
            history = json.dumps(list(st.session_state.history)) if include_history else None
            response = gennie_core.gennie_answer(user_message["content"], model_id, num_google_search_results, 1, date_restrict, history)
            # response = prompt
            # time.sleep(5)
            if not response:
                st.error("Some error has ocurred")
                return
            assistant_message = {"role": "assistant", "content": response}
            st.session_state.messages.append(assistant_message)
            message = f"Question: {prompt} \n{response}"
            st.session_state.history.append(message)
            with st.chat_message("user"):
                st.write(prompt)
            with st.chat_message("assistant"):
                st.write(response)
            logr(f"History: {st.session_state.history}")


if __name__ == "__main__":
    main()