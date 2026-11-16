"""Halaman EDA Liga. Rintisan; diisi pada tugas berikutnya."""
import streamlit as st


def tampil() -> None:
    st.subheader("EDA Liga")
    st.write(f"Klub saya: {st.session_state['klub']}. Halaman ini belum diisi.")
