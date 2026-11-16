"""Halaman History. Rintisan; diisi pada tugas berikutnya."""
import streamlit as st


def tampil() -> None:
    st.subheader("History")
    st.write(f"Klub saya: {st.session_state['klub']}. Halaman ini belum diisi.")
