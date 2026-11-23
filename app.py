"""Titik masuk: konfigurasi halaman, sidebar, tema, dan rute halaman."""
import streamlit as st

from gaya.komponen import pasang_tema, warna_aksen
from gaya.panel import TEAL
from halaman import eda_liga, history, overview, prediksi
from halaman.overview import SEMUA
from inti.data import klub_musim, muat_pertandingan
from inti.klub import warna_klub
from inti.model import muat_evaluasi, muat_model
from inti.sesi import JALUR_DATA, JALUR_METRIK, JALUR_MODEL, keterangan_cakupan

MUSIM_BERJALAN = "2026/27"
# kunci widget yang pilihannya harus bertahan saat pindah halaman
KUNCI_DIJAGA = ("fokus", "tren_metrik")  # rentang musim dijaga di halaman Overview

HALAMAN = {
    "Overview": overview.tampil,
    "Match Prediction": prediksi.tampil,
    "Analisis Liga": eda_liga.tampil,
    "History": history.tampil,
}


def _siapkan_sesi(df) -> None:
    """Isi session_state sekali: model, evaluasi, dan wadah skuad."""
    if "model" not in st.session_state:
        st.session_state["model"] = muat_model(str(JALUR_MODEL))
        st.session_state["evaluasi"] = muat_evaluasi(str(JALUR_METRIK))
    st.session_state.setdefault("skuad", {})
    st.session_state.setdefault("fokus", SEMUA)
    # Streamlit menghapus nilai widget yang tidak tampil di satu jalan skrip. Tanpa
    # penulisan ulang ini, filter klub dan rentang musim Overview kembali ke awal
    # setiap kali pengguna membuka Match Prediction lalu balik ke Overview.
    for kunci in KUNCI_DIJAGA:
        if kunci in st.session_state:
            st.session_state[kunci] = st.session_state[kunci]
    st.session_state.setdefault("musim", MUSIM_BERJALAN)
    if st.session_state.get("halaman") not in HALAMAN:
        st.session_state["halaman"] = "Overview"


def _sidebar(df, klub_daftar: list[str]) -> None:
    """Kontrol konteks untuk halaman selain Overview."""
    with st.sidebar:
        if st.session_state["halaman"] in {"Analisis Liga", "History"}:
            # Overview boleh memilih klub lama (mis. Bradford); halaman ini hanya
            # memuat klub musim berjalan, jadi pilihan lain dikembalikan ke semua klub.
            if st.session_state.get("fokus") not in [SEMUA] + klub_daftar:
                st.session_state["fokus"] = SEMUA
            st.selectbox("Fokus klub", [SEMUA] + klub_daftar, key="fokus")
        st.caption(keterangan_cakupan(df))


def _navigasi() -> None:
    """Navigasi tab di kolom kiri, membentang penuh dari atas ke bawah."""
    if st.session_state.get("halaman") not in HALAMAN:
        st.session_state["halaman"] = "Overview"
    with st.container(key="navigasi-kiri"):
        st.markdown("### Premier League")
        st.caption("Dashboard analisis")
        st.radio("Halaman", list(HALAMAN), key="halaman", label_visibility="collapsed")


def main() -> None:
    st.set_page_config(
        page_title="Dashboard Premier League",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    df = muat_pertandingan(str(JALUR_DATA))
    _siapkan_sesi(df)
    klub_daftar = klub_musim(df, MUSIM_BERJALAN)
    _sidebar(df, klub_daftar)

    fokus = st.session_state["fokus"]
    # klub lama yang dipilih di Overview tidak punya skuad atau jadwal musim berjalan
    st.session_state["klub"] = fokus if fokus in klub_daftar else klub_daftar[0]

    aksen = TEAL if fokus == SEMUA else warna_klub(fokus)
    pasang_tema(warna_aksen(aksen))
    kol_navigasi, kol_halaman = st.columns([1.5, 8.5], gap="small", vertical_alignment="top")
    with kol_navigasi:
        _navigasi()
    with kol_halaman:
        HALAMAN[st.session_state["halaman"]]()


if __name__ == "__main__":
    main()
