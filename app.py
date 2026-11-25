"""Titik masuk: konfigurasi halaman, sidebar, tema, dan rute halaman."""
from html import escape

import streamlit as st

from gaya.komponen import _uri_logo, pasang_tema, warna_aksen
from gaya.panel import TEAL
from halaman import landing
from inti.data import klub_musim, muat_pertandingan
from inti.klub import warna_klub
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

SEMUA = "Semua klub"  # sama dengan halaman.overview.SEMUA (pilihan klub "Premier League")


# Modul halaman dashboard dimuat saat dibuka, bukan saat aplikasi mulai: Altair dan scipy
# (model) memakan beberapa detik, dan landing page tidak membutuhkannya.
def _overview() -> None:
    from halaman import overview
    overview.tampil()


def _analisis() -> None:
    from halaman import analisis_laga
    analisis_laga.tampil()


def _history() -> None:
    from halaman import history
    history.tampil()


HALAMAN = {
    "Overview": _overview,
    "Match Analysis": _analisis,
    "History": _history,
}
# nilai ?buka=... dari tombol landing page -> tab dashboard yang dibuka
PINTU = {"overview": "Overview", "analisis": "Match Analysis", "history": "History"}


def _baca_tautan() -> None:
    """Tombol di landing page dan logo dashboard berupa tautan; baca lalu bersihkan URL-nya."""
    tujuan = st.query_params.get("buka")
    if tujuan in PINTU:
        st.session_state["masuk"] = True
        st.session_state["halaman"] = PINTU[tujuan]
        st.query_params.clear()
    elif st.query_params.get("beranda") is not None:
        st.session_state["masuk"] = False
        st.query_params.clear()


def _siapkan_sesi(df) -> None:
    """Isi session_state sekali: model, evaluasi, dan wadah skuad."""
    if "model" not in st.session_state:
        from inti.model import muat_evaluasi, muat_model
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
        # logo dan nama sekaligus tautan kembali ke landing page
        st.markdown(
            f'<a class="nav-merek" href="?beranda=1" target="_self" title="Kembali ke beranda">'
            f'{gambar}<span>Premier League: Dashboard Analysis</span></a>',
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
    _baca_tautan()
    if not st.session_state.get("masuk"):
        pasang_tema(TEAL)  # font, header Streamlit tersembunyi, dan token warna yang sama
        landing.tampil()
        return
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
