"""Halaman Overview. Rintisan; diisi pada tugas berikutnya."""
import streamlit as st


def tampil() -> None:
    st.subheader("Overview")
    st.write(f"Klub saya: {st.session_state['klub']}. Halaman ini belum diisi.")
