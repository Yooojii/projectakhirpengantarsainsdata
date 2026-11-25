"""Komponen visual papan taktik. Streamlit hanya dipakai di sini, bukan di inti/."""
import base64
import re
import threading
import zlib
from functools import lru_cache
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from inti.klub import NETRAL, logo_klub, singkatan

LATAR = "#F4F6F2"
GARIS = "#CFD6CC"
BATAS_KONTRAS = 4.5
_CSS = Path(__file__).with_name("tema.css")


def BACA_CSS() -> str:
    return _CSS.read_text(encoding="utf-8")


@lru_cache(maxsize=8)
def _padatkan_teks(css: str) -> str:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)       # komentar
    css = re.sub(r"\s+", " ", css)                           # spasi dan baris baru
    return re.sub(r"\s*([{};])\s*", r"\1", css).strip()      # spasi di sekitar { } ;


def padatkan_css(css: str) -> str:
    """CSS tanpa komentar dan spasi berlebih, untuk dikirim ke peramban.

    Tema dikirim ulang setiap kali halaman dijalankan ulang (setiap klik filter); komentar
    penjelasannya berguna di berkas sumber, bukan di peramban. Hasilnya disimpan per isi
    berkas, jadi suntingan CSS tetap langsung terbaca.
    """
    return _padatkan_teks(css)


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
        f"<style>{padatkan_css(BACA_CSS())}\n:root {{ --aksen: {warna_aksen(aksen)}; }}</style>",
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------ papan skor

def _persen(p: float) -> str:
    return f"{round(p * 100)}%"


# Logo klub di data/ berukuran 256 px (10-24 KB) padahal tampil 20-64 px, dan satu halaman bisa
# memuat puluhan logo yang sama. Mengirim versi kecil memangkas ukuran halaman History dan
# Match Analysis hingga ratusan KB per muat ulang.
LOGO_KECIL = 48    # tampil 20-24 px, dua kali lipat untuk layar retina
LOGO_SEDANG = 128  # tampil 56-64 px


@lru_cache(maxsize=None)
def _uri_logo(jalur: str, sisi: int | None = None) -> str:
    """Gambar PNG sebagai data URI; `sisi` memperkecilnya (sisi terpanjang, piksel) dan
    mengirimnya sebagai WebP, sekitar tiga kali lebih kecil dari PNG dengan transparansi utuh."""
    if sisi is None:
        with open(jalur, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    else:
        from io import BytesIO

        from PIL import Image
        with Image.open(jalur) as gambar:
            gambar = gambar.convert("RGBA")
            gambar.thumbnail((sisi, sisi), Image.LANCZOS)
            wadah = BytesIO()
            gambar.save(wadah, format="WEBP", quality=82, method=4)
    return "data:image/webp;base64," + base64.b64encode(wadah.getvalue()).decode("ascii")


# ---- logo sekali kirim per halaman ----
# Satu halaman bisa memuat logo klub yang sama puluhan kali (klasemen, daftar laga, lencana
# bentuk dan kartu keterangannya). Selama halaman dashboard digambar, setiap logo dicatat
# sekali sebagai variabel CSS (--lg-N) dan <img> hanya merujuk variabel itu; app.py lalu
# mengirim satu blok <style> berisi semua logo yang terpakai. Di luar itu (mis. tes atau
# landing page) logo tetap ditulis langsung di src seperti biasa. Catatan disimpan per utas
# karena tiap sesi Streamlit berjalan di utasnya sendiri.
_LOGO = threading.local()
_PIKSEL = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="


def mulai_kumpul_logo() -> None:
    _LOGO.daftar = {}


def selesai_kumpul_logo() -> str:
    """Blok <style> berisi semua logo yang dipakai halaman ini; catatan dikosongkan."""
    daftar = getattr(_LOGO, "daftar", None) or {}
    _LOGO.daftar = None
    if not daftar:
        return ""
    isi = ";".join(f'{nama}:url("{uri}")' for uri, nama in daftar.items())
    return f"<style>:root{{{isi}}}</style>"


def atribut_logo(jalur: str, sisi: int | None = None) -> str:
    """Atribut src (dan gaya) untuk <img> logo, memakai variabel CSS bila sedang mengumpulkan."""
    uri = _uri_logo(jalur, sisi)
    daftar = getattr(_LOGO, "daftar", None)
    if daftar is None:
        return f'src="{uri}"'
    # nama tetap per logo (bukan urutan pakai): saat filter diganti Streamlit memperbarui
    # halaman bertahap, dan blok <style> lama yang masih terpasang sesaat tetap menunjuk
    # ke logo yang benar
    nama = daftar.setdefault(uri, f"--lg-{zlib.crc32(uri.encode()):08x}")
    return f'src="{_PIKSEL}" style="background-image:var({nama})"'


def _lencana(klub: str) -> str:
    """Logo kecil (24 px, sama dengan tinggi nama), atau singkatan tiga huruf bila tak ada."""
    jalur = logo_klub(klub)
    if jalur is None:
        return f'<span class="papan-kode">{escape(singkatan(klub))}</span>'
    return f'<img class="papan-logo" {atribut_logo(str(jalur), LOGO_KECIL)} alt="" width="24" height="24">'


def angka_hitung(nilai: float, desimal: int = 0, tunda_ms: int | None = None) -> str:
    """Angka yang menghitung naik dari nol lewat CSS (`@property --hitung`), tanpa JavaScript.

    Bagian bulat dan pecahan dihitung sebagai dua penghitung terpisah, dipisah koma
    gaya Indonesia. Pembaca layar mendapat nilai akhirnya dari teks tersembunyi,
    karena isi `::after` tidak selalu dibacakan.
    """
    teks = f"{abs(nilai):.{desimal}f}"
    bulat, _, pecahan = teks.partition(".")
    tunda = f";--tunda:{tunda_ms}ms" if tunda_ms is not None else ""
    tanda = "-" if nilai < 0 and float(teks) != 0 else ""
    isi = f'{tanda}<span class="hitung" style="--akhir:{int(bulat)}{tunda}"></span>'
    if desimal:
        kelas = "hitung dua" if desimal == 2 else "hitung"
        isi += f',<span class="{kelas}" style="--akhir:{int(pecahan)}{tunda}"></span>'
    terbaca = tanda + teks.replace(".", ",")
    return f'<span class="sr">{terbaca}</span><span aria-hidden="true">{isi}</span>'


_BULAN_PENDEK = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
_KATA_HASIL = {"M": "Menang", "S": "Seri", "K": "Kalah"}


def lencana_laga(klub: str, laga, i: int = 0) -> str:
    """Lencana M/S/K satu laga dengan kartu keterangan yang muncul saat disorot atau difokus.

    `laga` adalah satu baris pertandingan (namedtuple dari itertuples) berisi tim_kandang,
    tim_tandang, gol_kandang, gol_tandang, hasil, dan tanggal. Kartu menulis laganya seperti
    papan skor: tuan rumah di kiri, tamu di kanan. Label untuk pembaca layar menyebut hasil
    dari sisi `klub` ("Menang 3-1 melawan Chelsea, tandang, ...").
    """
    kandang = laga.tim_kandang == klub
    lawan = laga.tim_tandang if kandang else laga.tim_kandang
    gk, gt = int(laga.gol_kandang), int(laga.gol_tandang)
    sendiri, kemasukan = (gk, gt) if kandang else (gt, gk)
    if laga.hasil == "D":
        hasil = "S"
    else:
        hasil = "M" if kandang == (laga.hasil == "H") else "K"
    tgl = laga.tanggal
    tanggal = f"{tgl.day} {_BULAN_PENDEK[tgl.month - 1]} {tgl.year}"
    tempat = "kandang" if kandang else "tandang"
    kata = _KATA_HASIL[hasil]
    label = f"{kata} {sendiri}-{kemasukan} melawan {lawan}, {tempat}, {tanggal}"
    return (
        f'<span class="{hasil}" style="--i:{i}" tabindex="0" aria-label="{escape(label)}">{hasil}'
        f'<span class="tip" aria-hidden="true">'
        f'<small>{tanggal}</small>'
        f'<span class="tip-laga"><b>{escape(laga.tim_kandang)}</b>{logo_kecil(laga.tim_kandang)}'
        f'<em>{gk} - {gt}</em>{logo_kecil(laga.tim_tandang)}<b>{escape(laga.tim_tandang)}</b></span>'
        '</span></span>'
    )


# nama dan NIM ditulis persis seperti yang diberikan kelompok
ANGGOTA = [
    ("Nadine Kinanti Azzahra", "M0401241025"),
    ("Yasmin Aufaahani Abdullah", "M0401241129"),
    ("Rizky Arif Wicaksono", "M0401241054"),
    ("Abdullah' ammar rabbaniyyin", "M0401241066"),
    ("Muhammad Shira Pramudita", "M0401241094"),
    ("Muhammad Alvaro Satria Priyambada", "M0401241100"),
]


def kaki_kelompok(kelas: str) -> str:
    """"© Kelompok 8"; arahkan kursor (atau fokus dengan Tab) untuk melihat anggota.

    Dipakai di rel navigasi dashboard (kelas "nav-kaki") dan di kaki landing page
    (kelas "lp-hak"); tampilannya diatur masing-masing lewat kelas pembungkus itu.
    """
    daftar = "".join(f"<li><b>{escape(nama)}</b><span>{escape(nim)}</span></li>" for nama, nim in ANGGOTA)
    return (
        f'<div class="{kelas}">&copy; '
        f'<span class="kelompok" tabindex="0" aria-describedby="anggota-{kelas}">Kelompok 8'
        f'<span class="anggota" id="anggota-{kelas}" role="tooltip"><small>Anggota kelompok</small>'
        f'<ul>{daftar}</ul></span></span></div>'
    )


def logo_kecil(klub: str, kelas: str = "logo-kecil") -> str:
    """Logo klub 20 px untuk daftar; singkatan dalam bulatan bila logonya tidak ada."""
    jalur = logo_klub(klub)
    if jalur is None:
        return f'<span class="kode-kecil">{escape(singkatan(klub))}</span>'
    return f'<img class="{kelas}" {atribut_logo(str(jalur), LOGO_KECIL)} alt="">'


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
                 label_y: str | None = None) -> "alt.Chart":
    """Grafik garis tanpa bingkai; satu deret disorot dengan aksen, sisanya #CFD6CC.

    `judul` adalah kalimat temuan dari pemanggil. `label_x`/`label_y` ditulis dengan kata
    (mis. "Gol per pertandingan"); bila kosong dipakai nama kolom tanpa garis bawah.
    """
    nama = [str(n) for n in data[seri].unique()]
    warna = [warna_aksen(aksen) if n == sorot else GARIS for n in nama]
    df = data.sort_values(x, kind="stable")  # garis digambar menurut urutan x, bukan urutan baris
    jelas = lambda kol: kol.replace("_", " ").capitalize()
    huruf = "IBM Plex Sans Condensed"

    import altair as alt  # impor lambat: modul ini juga dipakai landing page tanpa grafik Altair

    def lapis(bagian: pd.DataFrame, tebal: float) -> "alt.Chart":
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
