"""Halaman Team Styles: kategori gaya bermain klub hasil clustering K-Means (unsupervised)."""
from html import escape

import pandas as pd
import streamlit as st

from gaya.komponen import logo_kecil
from inti.sesi import AKAR

JALUR = AKAR / "data" / "klaster_gaya.csv"
WARNA = {"Elite": "#2E7D32", "Seimbang": "#1E88E5", "Menyerang": "#F57C00",
         "Bertahan": "#6D4C41", "Tumpul dan rapuh": "#9E9E9E"}
ARTI = {"Elite": "tajam menyerang sekaligus jarang kebobolan",
        "Seimbang": "di atas rata-rata liga di kedua sisi",
        "Menyerang": "serangan cukup hidup tapi pertahanan bocor",
        "Bertahan": "rapat di belakang tapi kurang tajam di depan",
        "Tumpul dan rapuh": "di bawah rata-rata liga di kedua sisi"}


@st.cache_data
def muat() -> pd.DataFrame:
    return pd.read_csv(JALUR)


PERINGKAT = [  # (judul, kolom, urut naik?, format nilai)
    ("Best attacking club", "indeks_serangan", False, "{:+.2f}"),
    ("Best defending club", "indeks_pertahanan", False, "{:+.2f}"),
    ("Paling produktif (gol per laga)", "gol", False, "{:.2f}"),
    ("Paling jarang kebobolan (per laga)", "gol_kebobolan", True, "{:.2f}"),
    ("Paling rajin menembak (per laga)", "tembakan", False, "{:.1f}"),
    ("Paling banyak sepak pojok (per laga)", "sepak_pojok", False, "{:.1f}"),
    ("Worst attacking club", "indeks_serangan", True, "{:+.2f}"),
    ("Worst defending club", "indeks_pertahanan", True, "{:+.2f}"),
    ("Penyelesaian paling klinis (gol per tembakan tepat)", "gol_per_tepat", False, "{:.2f}"),
    ("Paling boros peluang (tembakan per gol)", "tembakan_per_gol", False, "{:.1f}"),
    ("Raja penguasaan bola (%)", "penguasaan_bola", False, "{:.1f}"),
    ("Akurasi umpan terbaik (%)", "akurasi_umpan", False, "{:.1f}"),
    ("Comeback king (poin setelah tertinggal saat jeda)", "poin_comeback", False, "{:.0f}"),
    ("Paling sering kehilangan keunggulan (laga)", "hilang_unggul", False, "{:.0f}"),
    ("Tim babak kedua (selisih gol babak kedua)", "selisih_babak2", False, "{:+.0f}"),
    ("Clean sheet terbanyak", "clean_sheet", False, "{:.0f}"),
    ("Benteng kandang terkuat (poin per laga)", "poin_kandang", False, "{:.2f}"),
    ("Jago tandang (poin per laga)", "poin_tandang", False, "{:.2f}"),
    ("Tim paling kasar (kartu per laga)", "kartu", False, "{:.2f}"),
    ("Tim paling bersih (kartu per laga)", "kartu", True, "{:.2f}"),
]


def _top5(sub: pd.DataFrame, judul: str, kolom: str, naik: bool, fmt: str) -> str:
    atas = sub.dropna(subset=[kolom]).sort_values(kolom, ascending=naik).head(5)
    baris = "".join(
        f'<tr><td style="width:2rem">{i}</td><td style="width:2.2rem">{logo}</td>'
        f'<td style="text-align:left">{escape(r.klub)}<br>'
        f'<small style="color:{WARNA[r.kategori]}">{r.kategori}</small></td>'
        f'<td><b>{fmt.format(getattr(r, kolom))}</b></td></tr>'
        for i, r in enumerate(atas.itertuples(), 1)
        for logo in [logo_kecil(r.klub).replace("<img ", '<img style="width:20px;min-width:20px" ')])
    return (f'<div class="blok"><div class="blok-judul"><b>{judul}</b></div>'
            f'<table class="tabel" style="width:100%"><tbody>{baris}</tbody></table></div>')


def tampil() -> None:
    df = muat()
    daftar = sorted(df.musim.unique(), reverse=True)
    kol_judul, kol_musim = st.columns([4, 1.3], vertical_alignment="top")
    with kol_judul:
        st.markdown('<div class="kepala-hal"><div><h2>Team Styles</h2>'
                    '<p>Klub dikelompokkan dengan K-Means dari statistik serangan dan pertahanan per laga.</p>'
                    '</div></div>', unsafe_allow_html=True)
    with kol_musim:
        musim = st.selectbox("Musim", daftar, key="gaya_musim")
    sub = df[df.musim == musim].copy()

    kol = st.columns(2)
    ada = [p for p in PERINGKAT if sub[p[1]].notna().any()]  # penguasaan bola baru ada sejak 2022/23
    for i, (judul, kolom, naik, fmt) in enumerate(ada):
        kol[i % 2].markdown(_top5(sub, judul, kolom, naik, fmt), unsafe_allow_html=True)

    baris = []
    for nama, warna in WARNA.items():
        klub = sub[sub.kategori == nama].sort_values("poin", ascending=False).klub
        if klub.empty:
            continue
        baris.append(f'<tr><td style="text-align:left;width:38%"><b style="color:{warna}">{nama}</b><br><small>{ARTI[nama]}</small></td>'
                     f'<td style="text-align:left">{escape(", ".join(klub))}</td></tr>')
    st.markdown(f'<div class="blok"><div class="blok-judul"><b>Kategori musim {musim}</b></div>'
                f'<table class="tabel"><tbody>{"".join(baris)}</tbody></table></div>',
                unsafe_allow_html=True)
    st.caption("Indeks dibakukan per musim dari gol, tembakan, tembakan tepat, dan sepak pojok "
               "(serangan) serta gol, tembakan, dan tembakan tepat lawan (pertahanan). "
               "K-Means dengan 5 klaster dilatih pada 540 klub-musim sejak 2000/01.")
