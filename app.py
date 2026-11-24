"""Titik masuk: konfigurasi halaman, sidebar, tema, dan rute halaman."""
import streamlit as st

from gaya.komponen import _uri_logo, pasang_tema, warna_aksen
from gaya.panel import TEAL
from halaman import analisis_laga, history, overview
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
    "Match Analysis": analisis_laga.tampil,
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
        st.caption(keterangan_cakupan(df))


def _navigasi(df) -> None:
    """Rel navigasi navy di kolom kiri, menempel saat halaman digulir."""
    if st.session_state.get("halaman") not in HALAMAN:
        st.session_state["halaman"] = "Overview"
    logo = JALUR_DATA.parent / "premier league logo.png"
    gambar = f'<img src="{_uri_logo(str(logo))}" alt="">' if logo.is_file() else ""
    with st.container(key="navigasi-kiri"):
        st.markdown(
            f'<div class="nav-merek">{gambar}<div><b>Premier League</b>'
            f'<span>Dashboard analisis</span></div></div>',
            unsafe_allow_html=True,
        )
        st.radio("Halaman", list(HALAMAN), key="halaman", label_visibility="collapsed")
        st.markdown(f'<div class="nav-kaki">{keterangan_cakupan(df)}</div>', unsafe_allow_html=True)


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
        _navigasi(df)
    with kol_halaman:
        HALAMAN[st.session_state["halaman"]]()


if __name__ == "__main__":
    main()
