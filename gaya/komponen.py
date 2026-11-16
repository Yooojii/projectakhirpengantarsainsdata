"""Komponen visual papan taktik. Streamlit hanya dipakai di sini, bukan di inti/."""
import base64
from functools import lru_cache
from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from inti.klub import NETRAL, logo_klub, singkatan

LATAR = "#F4F6F2"
GARIS = "#CFD6CC"
BATAS_KONTRAS = 4.5
_CSS = Path(__file__).with_name("tema.css")


def BACA_CSS() -> str:
    return _CSS.read_text(encoding="utf-8")


# ----------------------------------------------------------------- warna aksen

def _luminans(heks: str) -> float:
    kanal = []
    for i in (1, 3, 5):
        c = int(heks[i:i + 2], 16) / 255
        kanal.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kanal[0] + 0.7152 * kanal[1] + 0.0722 * kanal[2]


def _kontras(a: str, b: str = LATAR) -> float:
    la, lb = sorted((_luminans(a), _luminans(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def warna_aksen(hex: str) -> str:
    """Gelapkan warna klub ke arah rona yang sama sampai kontras terhadap latar >= 4,5:1.

    Warna yang sudah lolos dikembalikan apa adanya (huruf besar). Warna asli klub
    tetap di inti/klub.py; penyesuaian ini hanya urusan tampilan.
    """
    hex = hex.upper()
    if _kontras(hex) >= BATAS_KONTRAS:
        return hex
    rgb = [int(hex[i:i + 2], 16) for i in (1, 3, 5)]
    faktor = 1.0
    while faktor > 0:
        faktor -= 0.01
        kandidat = "#" + "".join(f"{round(c * faktor):02X}" for c in rgb)
        if _kontras(kandidat) >= BATAS_KONTRAS:
            return kandidat
    return "#000000"


def pasang_tema(aksen: str) -> None:
    """Suntikkan tema.css satu kali per jalan skrip; tulis ulang --aksen untuk klub terpilih."""
    st.markdown(
        f"<style>{BACA_CSS()}\n:root {{ --aksen: {warna_aksen(aksen)}; }}</style>",
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------ papan skor

def _persen(p: float) -> str:
    return f"{round(p * 100)}%"


@lru_cache(maxsize=None)
def _uri_logo(jalur: str) -> str:
    with open(jalur, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def _lencana(klub: str) -> str:
    """Logo kecil (24 px, sama dengan tinggi nama), atau singkatan tiga huruf bila tak ada."""
    jalur = logo_klub(klub)
    if jalur is None:
        return f'<span class="papan-kode">{escape(singkatan(klub))}</span>'
    return f'<img class="papan-logo" src="{_uri_logo(str(jalur))}" alt="" width="24" height="24">'


def papan_skor(klub_k: str, klub_t: str, skor: tuple, peluang: dict, aksen: str,
               berubah: bool = False) -> str:
    """Kandang di kiri, skor di dalam lingkaran, tamu di kanan; garis tengah terputus di lingkaran.

    `berubah=True` menambahkan kelas yang menjalankan satu-satunya transisi warna pada angka
    peluang. Halaman hanya boleh memberikannya ketika penggeser benar-benar bergerak; kalau
    selalu True, angka beranimasi saat halaman dimuat, dan itu dilarang.
    `aksen` diterima demi kontrak antarmuka; papan sendiri tidak berwarna.
    """
    k, t = escape(klub_k), escape(klub_t)
    kelas = "angka-prediksi berubah" if berubah else "angka-prediksi"
    return (
        '<div class="papan-skor">'
        '<div class="papan-baris">'
        f'<div class="papan-sisi papan-kandang"><span class="papan-nama">{k}{_lencana(klub_k)}</span></div>'
        '<div class="papan-lingkaran">'
        f'<span class="papan-skor-angka">{int(skor[0])}</span>'
        '<span class="papan-skor-angka">:</span>'
        f'<span class="papan-skor-angka">{int(skor[1])}</span>'
        '</div>'
        f'<div class="papan-sisi papan-tamu"><span class="papan-nama">{_lencana(klub_t)}{t}</span></div>'
        '</div>'
        '<div class="papan-peluang">'
        f'<div class="kandang"><span class="{kelas}">{_persen(peluang["menang"])}</span>'
        '<span class="keterangan">Kandang menang</span></div>'
        f'<div class="seri"><span class="{kelas}">{_persen(peluang["seri"])}</span>'
        '<span class="keterangan">Seri</span></div>'
        f'<div class="tamu"><span class="{kelas}">{_persen(peluang["kalah"])}</span>'
        '<span class="keterangan">Tamu menang</span></div>'
        '</div></div>'
    )


# ----------------------------------------------------------------- bar atribut

def bar_atribut(nilai: int, aksen: str | None) -> str:
    """Delapan ruas, terisi menurut nilai 0-99. Aksen untuk klub saya, abu-abu bila None."""
    warna = NETRAL if aksen is None else warna_aksen(aksen)
    isi = max(0, min(8, round(nilai / 99 * 8)))
    ruas = "".join(
        f'<span class="ruas terisi" style="background:{warna}"></span>' if i < isi
        else '<span class="ruas"></span>'
        for i in range(8)
    )
    return (
        f'<div class="bar-atribut"><div class="bar-isi">{ruas}</div>'
        f'<span class="angka">{int(nilai)}</span></div>'
    )


# ---------------------------------------------------------------- grafik dasar

def grafik_dasar(data: pd.DataFrame, x: str, y: str, judul: str, sorot: str | None,
                 aksen: str, seri: str = "klub", label_x: str | None = None,
                 label_y: str | None = None) -> alt.Chart:
    """Grafik garis tanpa bingkai; satu deret disorot dengan aksen, sisanya #CFD6CC.

    `judul` adalah kalimat temuan dari pemanggil. `label_x`/`label_y` ditulis dengan kata
    (mis. "Gol per pertandingan"); bila kosong dipakai nama kolom tanpa garis bawah.
    """
    nama = [str(n) for n in data[seri].unique()]
    warna = [warna_aksen(aksen) if n == sorot else GARIS for n in nama]
    df = data.sort_values(x, kind="stable")  # garis digambar menurut urutan x, bukan urutan baris
    jelas = lambda kol: kol.replace("_", " ").capitalize()
    huruf = "IBM Plex Sans Condensed"

    def lapis(bagian: pd.DataFrame, tebal: float) -> alt.Chart:
        return alt.Chart(bagian).mark_line(interpolate="monotone", strokeWidth=tebal).encode(
            x=alt.X(x, title=label_x or jelas(x), axis=alt.Axis(grid=False)),
            y=alt.Y(y, title=label_y or jelas(y), axis=alt.Axis(grid=True)),
            color=alt.Color(f"{seri}:N", scale=alt.Scale(domain=nama, range=warna), legend=None),
            tooltip=[seri, x, y],
        )

    lapisan = [lapis(df[df[seri] != sorot], 1.5)]
    if sorot is not None:  # lapisan terpisah supaya deret sorotan digambar paling atas
        lapisan.append(lapis(df[df[seri] == sorot], 3))
    return (
        alt.layer(*lapisan)
        .properties(title=judul)
        .configure_view(stroke=None)
        .configure_axis(domain=False, ticks=False, labelColor="#65736C", titleColor="#65736C",
                        labelFont=huruf, titleFont="IBM Plex Sans", titleFontWeight=400,
                        labelFontSize=13, titleFontSize=13)
        .configure_axisX(grid=False)
        .configure_axisY(grid=True, gridColor=GARIS, gridWidth=1)
        .configure_title(anchor="start", font="IBM Plex Sans", fontSize=22, fontWeight=600,
                         color="#0E1F18")
    )
