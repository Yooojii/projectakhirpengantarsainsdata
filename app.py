"""Titik masuk: konfigurasi halaman, sidebar, tema, dan rute halaman."""
from html import escape

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

# nama dan NIM ditulis persis seperti yang diberikan kelompok
ANGGOTA = [
    ("Nadine Kinanti Azzahra", "M0401241025"),
    ("Yasmin Aufaahani Abdullah", "M0401241129"),
    ("Rizky Arif Wicaksono", "M0401241054"),
    ("Abdullah' ammar rabbaniyyin", "M0401241066"),
    ("Muhammad Shira Pramudita", "M0401241094"),
    ("Muhammad Alvaro Satria Priyambada", "M0401241100"),
]

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


def _kaki_kelompok() -> str:
    """"© Kelompok 8"; arahkan kursor (atau fokus dengan Tab) untuk melihat anggota."""
    daftar = "".join(f"<li><b>{escape(nama)}</b><span>{escape(nim)}</span></li>" for nama, nim in ANGGOTA)
    return (
        '<div class="nav-kaki">&copy; '
        '<span class="kelompok" tabindex="0" aria-describedby="anggota-kelompok">Kelompok 8'
        f'<span class="anggota" id="anggota-kelompok" role="tooltip"><small>Anggota kelompok</small>'
        f'<ul>{daftar}</ul></span></span></div>'
    )


def _navigasi(df) -> None:
    """Rel navigasi navy di kolom kiri, menempel saat halaman digulir."""
    if st.session_state.get("halaman") not in HALAMAN:
        st.session_state["halaman"] = "Overview"
    # lambang BallBoard tanpa tulisan (256 px, 10 KB), dipotong dari logo transparan buatan tim
    # "BallBoard Soccer Analytics Logo Transparan.png" (1,2 MB, terlalu berat untuk tiap halaman)
    logo = JALUR_DATA.parent / "ballboard_logo.png"
    gambar = f'<img src="{_uri_logo(str(logo))}" alt="BallBoard">' if logo.is_file() else ""
    with st.container(key="navigasi-kiri"):
        st.markdown(
            f'<div class="nav-merek">{gambar}<span>Premier League: Dashboard Analysis</span></div>',
            unsafe_allow_html=True,
        )
        st.radio("Halaman", list(HALAMAN), key="halaman", label_visibility="collapsed")
        st.markdown(_kaki_kelompok(), unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="BallBoard: Premier League Dashboard Analysis",
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
