"""Titik masuk: konfigurasi halaman, sidebar, tema, dan rute halaman."""
import streamlit as st

from gaya.komponen import pasang_tema, warna_aksen
from halaman import eda_liga, history, overview, prediksi
from inti.data import klub_musim, muat_pertandingan
from inti.klub import logo_klub, singkatan, warna_klub
from inti.model import muat_evaluasi, muat_model
from inti.sesi import JALUR_DATA, JALUR_METRIK, JALUR_MODEL, keterangan_cakupan

MUSIM_BERJALAN = "2026/27"

HALAMAN = {
    "Overview": overview.tampil,
    "EDA Liga": eda_liga.tampil,
    "History": history.tampil,
    "Prediksi & Simulasi": prediksi.tampil,
}


def _siapkan_sesi(df) -> None:
    """Isi session_state sekali: model, evaluasi, dan wadah skuad."""
    if "model" not in st.session_state:
        st.session_state["model"] = muat_model(str(JALUR_MODEL))
        st.session_state["evaluasi"] = muat_evaluasi(str(JALUR_METRIK))
    st.session_state.setdefault("skuad", {})


def _sidebar(df) -> None:
    klub_daftar = klub_musim(df, MUSIM_BERJALAN)
    with st.sidebar:
        jalur = logo_klub(st.session_state.get("klub", klub_daftar[0]))
        if jalur is not None:
            st.image(str(jalur), width=24)
        else:
            st.write(singkatan(st.session_state.get("klub", klub_daftar[0])))
        st.selectbox("Klub saya", klub_daftar, key="klub")
        st.radio("Halaman", list(HALAMAN), key="halaman", label_visibility="collapsed")
        st.caption(keterangan_cakupan(df))


def main() -> None:
    st.set_page_config(page_title="Dashboard Premier League", layout="wide")
    df = muat_pertandingan(str(JALUR_DATA))
    _siapkan_sesi(df)
    _sidebar(df)
    pasang_tema(warna_aksen(warna_klub(st.session_state["klub"])))
    HALAMAN[st.session_state["halaman"]]()


if __name__ == "__main__":
    main()
