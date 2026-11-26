"""Halaman Team Styles: kategori gaya bermain klub hasil clustering K-Means (unsupervised).

Tiga bagian, dari gambaran besar ke rincian:
1. Peta gaya bermain: setiap klub diletakkan menurut indeks serangan (sumbu datar) dan indeks
   pertahanan (sumbu tegak). Garis tengah adalah rata-rata liga musim itu.
2. Kategori: lima klaster K-Means beserta artinya dan klub yang masuk.
3. Peringkat: 20 daftar lima besar, dikelompokkan per tema supaya halaman tidak memanjang.

Semua gerak memakai @keyframes yang sudah ada di tema.css dan ikut mati bila pengguna memilih
mengurangi gerakan (prefers-reduced-motion).
"""
from html import escape

import pandas as pd
import streamlit as st

from gaya.komponen import logo_kecil
from inti.sesi import AKAR

JALUR = AKAR / "data" / "klaster_gaya.csv"

# Warna kategori diselaraskan dengan palet dashboard; semuanya kontras >= 4,5:1 di atas putih,
# jadi aman dipakai untuk teks maupun titik.
WARNA = {"Title Contenders": "#157D7B", "Well-Balanced": "#2F6F8A", "Attack-Minded": "#B4470D",
         "Defence-First": "#6B4E9B", "Struggling": "#5F7883"}
ARTI = {"Title Contenders": "Strong at both ends",
        "Well-Balanced": "Above average at both ends",
        "Attack-Minded": "Score plenty, concede plenty",
        "Defence-First": "Hard to beat, few goals",
        "Struggling": "Below average at both ends"}

# Batas sumbu peta tetap untuk semua musim (data 2000/01-2026/27 berkisar -2,3 sampai 2,7),
# supaya posisi klub bisa dibandingkan antarmusim.
BATAS = 2.8


@st.cache_data
def muat() -> pd.DataFrame:
    return pd.read_csv(JALUR)


# (judul, kolom, kecil lebih baik?, format nilai, satuan singkat)
PERINGKAT = {
    "Serangan": [
        ("Serangan terbaik", "indeks_serangan", False, "{:+.2f}", "indeks"),
        ("Paling produktif", "gol", False, "{:.2f}", "gol per laga"),
        ("Paling rajin menembak", "tembakan", False, "{:.1f}", "tembakan per laga"),
        ("Paling banyak sepak pojok", "sepak_pojok", False, "{:.1f}", "per laga"),
    ],
    "Pertahanan": [
        ("Pertahanan terbaik", "indeks_pertahanan", False, "{:+.2f}", "indeks"),
        ("Paling jarang kebobolan", "gol_kebobolan", True, "{:.2f}", "gol per laga"),
        ("Clean sheet terbanyak", "clean_sheet", False, "{:.0f}", "laga"),
        ("Benteng kandang terkuat", "poin_kandang", False, "{:.2f}", "poin per laga"),
    ],
    "Efisiensi": [
        ("Penyelesaian paling klinis", "gol_per_tepat", False, "{:.2f}", "gol per tembakan tepat"),
        ("Paling boros peluang", "tembakan_per_gol", False, "{:.1f}", "tembakan per gol"),
        ("Raja penguasaan bola", "penguasaan_bola", False, "{:.1f}", "% penguasaan"),
        ("Akurasi umpan terbaik", "akurasi_umpan", False, "{:.1f}", "% umpan tepat"),
    ],
    "Mental": [
        ("Raja comeback", "poin_comeback", False, "{:.0f}", "poin setelah tertinggal saat jeda"),
        ("Paling sering kehilangan keunggulan", "hilang_unggul", False, "{:.0f}", "laga"),
        ("Tim babak kedua", "selisih_babak2", False, "{:+.0f}", "selisih gol babak kedua"),
        ("Jago tandang", "poin_tandang", False, "{:.2f}", "poin per laga"),
    ],
    "Disiplin dan terlemah": [
        ("Tim paling bersih", "kartu", True, "{:.2f}", "kartu per laga"),
        ("Tim paling kasar", "kartu", False, "{:.2f}", "kartu per laga"),
        ("Serangan terlemah", "indeks_serangan", True, "{:+.2f}", "indeks"),
        ("Pertahanan terlemah", "indeks_pertahanan", True, "{:+.2f}", "indeks"),
    ],
}


def _posisi(v: float) -> float:
    """Indeks ke persen sumbu (0-100), dijepit supaya logo tidak keluar bidang."""
    return min(max((v + BATAS) / (2 * BATAS) * 100, 4.0), 96.0)


def _koma(teks: str) -> str:
    return teks.replace(".", ",")


def peta(sub: pd.DataFrame, musim: str) -> str:
    """Bidang serangan x pertahanan; setiap klub berupa logo berbingkai warna kategorinya."""
    # Streamlit memakai ulang elemen HTML yang sama saat musim berganti dan hanya mengubah
    # atributnya. Titik diurutkan per nama klub, jadi elemen ke-n kebanyakan tetap klub yang
    # sama dan transisi CSS pada left/bottom membuatnya meluncur ke posisi musim baru.
    # Urutan kemunculan pertama (--i) tetap mengikuti poin, dari yang tertinggi.
    urut = sub.sort_values("klub").reset_index(drop=True)
    peringkat_poin = urut["poin"].rank(ascending=False, method="first").astype(int) - 1
    titik = []
    for _, r in urut.iterrows():
        i = int(peringkat_poin[_])
        x, y = _posisi(r.indeks_serangan), _posisi(r.indeks_pertahanan)
        warna = WARNA.get(r.kategori, "#5F7883")
        label = (f"{r.klub}, {r.kategori}. Indeks serangan {_koma(f'{r.indeks_serangan:+.2f}')}, "
                 f"pertahanan {_koma(f'{r.indeks_pertahanan:+.2f}')}, {int(r.poin)} poin dari {int(r.main)} laga")
        sisi = "kiri" if x > 60 else "kanan"  # kartu keterangan membuka ke ruang yang lapang
        titik.append(
            f'<span class="peta-titik {sisi}" tabindex="0" aria-label="{escape(label)}" '
            f'style="left:{x:.1f}%;bottom:{y:.1f}%;--warna:{warna};--i:{i}">'
            f'{logo_kecil(r.klub, "peta-logo")}'
            f'<span class="peta-tip" aria-hidden="true"><b>{escape(r.klub)}</b>'
            f'<i style="color:{warna}">{escape(r.kategori)}</i>'
            f'<small>Serangan {_koma(f"{r.indeks_serangan:+.2f}")}, '
            f'pertahanan {_koma(f"{r.indeks_pertahanan:+.2f}")}</small>'
            f'<small>{int(r.poin)} poin dari {int(r.main)} laga</small></span></span>'
        )
    kuadran = (
        '<div class="peta-kuadran ka">Strong both ends</div>'
        '<div class="peta-kuadran ki">Defence-first</div>'
        '<div class="peta-kuadran ba">Attack-minded</div>'
        '<div class="peta-kuadran bi">Struggling</div>'
    )
    return (
        '<div class="blok gaya-peta"><div class="blok-judul"><b>Peta gaya bermain</b>'
        f'<span>{len(urut)} klub, musim {escape(musim)}</span></div>'
        '<div class="peta-bingkai">'
        '<span class="peta-sumbu-y">Pertahanan, makin atas makin rapat</span>'
        f'<div class="peta-bidang" role="group" aria-label="Peta gaya bermain musim {escape(musim)}">'
        f'{kuadran}<i class="peta-garis datar"></i><i class="peta-garis tegak"></i>'
        f'{"".join(titik)}</div>'
        '<span class="peta-sumbu-x">Serangan, makin kanan makin tajam</span>'
        '</div>'
        '<p class="peta-ket">Garis putus-putus adalah rata-rata liga musim ini.</p></div>'
    )


def kategori(sub: pd.DataFrame, musim: str, putar: str = "") -> str:
    """Lima kategori K-Means: arti singkat dan logo klubnya, urut poin."""
    baris = []
    for j, (nama, warna) in enumerate(WARNA.items()):
        klub = sub[sub.kategori == nama].sort_values("poin", ascending=False).klub.tolist()
        if klub:
            logo = "".join(
                f'<span class="kat-logo" style="--i:{k}" title="{escape(n)}">{logo_kecil(n)}'
                f'<span class="sr">{escape(n)}</span></span>'
                for k, n in enumerate(klub))
        else:
            logo = '<span class="kat-kosong">Tidak ada klub musim ini</span>'
        baris.append(
            f'<div class="kat-baris" style="--warna:{warna};--j:{j}">'
            f'<div class="kat-kepala"><b style="color:{warna}">{nama}</b>'
            f'<span class="kat-jumlah">{len(klub)} klub</span></div>'
            f'<p>{ARTI[nama]}</p><div class="kat-logo-baris">{logo}</div></div>'
        )
    return (f'<div class="blok gaya-kategori{putar}"><div class="blok-judul"><b>Kategori gaya</b>'
            f'<span>musim {escape(musim)}</span></div>{"".join(baris)}</div>')


def _peringkat(sub: pd.DataFrame, judul: str, kolom: str, naik: bool, fmt: str, satuan: str,
               urutan: int) -> str:
    """Satu daftar lima besar; batang menunjukkan nilai relatif terhadap peringkat pertama."""
    atas = sub.dropna(subset=[kolom]).sort_values(kolom, ascending=naik).head(5)
    if atas.empty:
        return ""
    nilai = atas[kolom].abs()
    puncak = nilai.max() or 1.0
    terkecil = nilai.min() or 1.0
    baris = []
    for i, r in enumerate(atas.itertuples(), 1):
        v = abs(getattr(r, kolom))
        # untuk "kecil lebih baik", peringkat pertama tetap batang terpanjang
        lebar = (terkecil / v if v else 1.0) if naik else v / puncak
        warna = WARNA.get(r.kategori, "#5F7883")
        baris.append(
            f'<li style="--i:{i - 1}"><span class="rk-no">{i}</span>{logo_kecil(r.klub)}'
            f'<span class="rk-nama"><b>{escape(r.klub)}</b>'
            f'<small style="color:{warna}">{escape(r.kategori)}</small></span>'
            f'<span class="rk-nilai">{_koma(fmt.format(getattr(r, kolom)))}</span>'
            f'<span class="rk-lajur"><i style="width:{100 * max(lebar, 0.04):.1f}%;background:{warna}"></i></span></li>'
        )
    return (f'<div class="rk-kartu" style="--urutan:{urutan}"><div class="rk-judul"><b>{judul}</b>'
            f'<span>{escape(satuan)}</span></div><ol class="rk-daftar">{"".join(baris)}</ol></div>')


def _putaran(nama: str, pilihan: tuple) -> str:
    """Kelas "putar-b" yang bergantian setiap kali `pilihan` berubah.

    Streamlit memakai ulang elemen HTML yang sama saat halaman dijalankan ulang dan hanya
    mengganti isinya, jadi animasi masuk yang sudah selesai tidak diputar lagi. Peramban
    selalu memutar ulang animasi yang namanya berubah; kelas ini menukar nama animasi ke
    kembarannya (isi sama, nama beda) setiap kali tema atau musim berganti.
    """
    lalu = st.session_state.get(f"_{nama}_pilihan")
    balik = st.session_state.get(f"_{nama}_balik", False)
    if lalu is not None and lalu != pilihan:
        balik = not balik
    st.session_state[f"_{nama}_pilihan"] = pilihan
    st.session_state[f"_{nama}_balik"] = balik
    return " putar-b" if balik else ""


def tampil() -> None:
    df = muat()
    daftar = sorted(df.musim.unique(), reverse=True)
    kol_judul, kol_musim = st.columns([4, 1.3], vertical_alignment="top")
    with kol_judul:
        st.markdown('<div class="kepala-hal"><div><h2>Team Styles</h2>'
                    '<p>Gaya bermain klub, dikelompokkan dengan K-Means dari statistik serangan '
                    'dan pertahanan per laga.</p></div></div>', unsafe_allow_html=True)
    with kol_musim:
        musim = st.selectbox("Musim", daftar, key="gaya_musim")
    sub = df[df.musim == musim].copy()

    with st.container(key="gaya-atas"):
        kol_peta, kol_kat = st.columns([1.45, 1], gap="medium", vertical_alignment="top")
        with kol_peta:
            st.markdown(peta(sub, musim), unsafe_allow_html=True)
        with kol_kat:
            # ganti musim: baris dan logo kategori muncul bergantian lagi
            st.markdown(kategori(sub, musim, _putaran("gaya_kat", (musim,))), unsafe_allow_html=True)

    with st.container(key="gaya-peringkat"):
        st.markdown('<div class="rk-kepala"><b>Peringkat klub</b></div>', unsafe_allow_html=True)
        tema = st.pills("Tema peringkat", list(PERINGKAT), default="Serangan", key="gaya_tema",
                        label_visibility="collapsed") or "Serangan"
        kartu = "".join(_peringkat(sub, *p, urutan=i) for i, p in enumerate(PERINGKAT[tema]))
        if not kartu:
            kartu = '<div class="kartu-kosong">Data untuk tema ini belum tersedia di musim ini.</div>'
        # ganti tema atau musim: kartu naik dan batang tumbuh lagi
        putar = _putaran("gaya_rk", (tema, musim))
        st.markdown(f'<div class="rk-grid{putar}">{kartu}</div>', unsafe_allow_html=True)

    st.caption("Indeks dibakukan per musim dari gol, tembakan, tembakan tepat, dan sepak pojok "
               "(serangan) serta gol, tembakan, dan tembakan tepat lawan (pertahanan). "
               "K-Means dengan 5 klaster dilatih pada 540 klub-musim sejak 2000/01.")
