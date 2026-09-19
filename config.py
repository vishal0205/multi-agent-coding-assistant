import os
from dotenv import load_dotenv

load_dotenv()

def get_secret(key: str) -> str:
    """Reads from Streamlit secrets on Streamlit Cloud, falls back to .env locally."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)