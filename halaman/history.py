"""Halaman History: rekor pertemuan historis, bentuk permainan, dan klasemen."""
from html import escape
import pandas as pd
import streamlit as st

from gaya.komponen import _uri_logo, angka_hitung, logo_kecil, warna_aksen
from inti.data import klub_musim, muat_pertandingan
from inti.klub import logo_klub, singkatan, warna_klub
from inti.sesi import BULAN, JALUR_DATA

MUSIM_BERJALAN = "2026/27"
KABUT = "#8FA6B0"


def rekor_pertemuan(df: pd.DataFrame, klub_a: str, klub_b: str) -> dict:
    """Rekor head-to-head seluruh pertemuan dari sudut pandang klub_a."""
    laga_ab = df[(df["tim_kandang"] == klub_a) & (df["tim_tandang"] == klub_b)]
    laga_ba = df[(df["tim_kandang"] == klub_b) & (df["tim_tandang"] == klub_a)]

    menang = int((laga_ab["hasil"] == "H").sum() + (laga_ba["hasil"] == "A").sum())
    seri = int((laga_ab["hasil"] == "D").sum() + (laga_ba["hasil"] == "D").sum())
    kalah = int((laga_ab["hasil"] == "A").sum() + (laga_ba["hasil"] == "H").sum())
    total = menang + seri + kalah

    return {"menang": menang, "seri": seri, "kalah": kalah, "total": total}


def keadaan_riwayat(total: int) -> str:
    """Status riwayat pertemuan: kosong (0), tipis (1-3), penuh (>=4)."""
    if total == 0:
        return "kosong"
    elif total < 4:
        return "tipis"
    return "penuh"


def klasemen(df: pd.DataFrame, musim: str) -> pd.DataFrame:
    """Tabel klasemen lengkap untuk musim tertentu terurut menurun berdasarkan poin."""
    sub = df[df["musim"] == musim]
    klub_list = sorted(set(sub["tim_kandang"]) | set(sub["tim_tandang"]))

    baris = []
    for k in klub_list:
        kandang = sub[sub["tim_kandang"] == k]
        tandang = sub[sub["tim_tandang"] == k]

        m_k = int((kandang["hasil"] == "H").sum())
        s_k = int((kandang["hasil"] == "D").sum())
        k_k = int((kandang["hasil"] == "A").sum())
        gm_k = int(kandang["gol_kandang"].sum())
        gk_k = int(kandang["gol_tandang"].sum())

        m_t = int((tandang["hasil"] == "A").sum())
        s_t = int((tandang["hasil"] == "D").sum())
        k_t = int((tandang["hasil"] == "H").sum())
        gm_t = int(tandang["gol_tandang"].sum())
        gk_t = int(tandang["gol_kandang"].sum())

        main = len(kandang) + len(tandang)
        menang = m_k + m_t
        seri = s_k + s_t
        kalah = k_k + k_t
        gm = gm_k + gm_t
        gk = gk_k + gk_t
        selisih = gm - gk
        poin = menang * 3 + seri * 1

        baris.append({
            "klub": k,
            "main": main,
            "menang": menang,
            "seri": seri,
            "kalah": kalah,
            "gol_memasukkan": gm,
            "gol_kemasukan": gk,
            "selisih": selisih,
            "poin": poin,
        })

    res = pd.DataFrame(baris)
    res = res.sort_values(
        by=["poin", "selisih", "gol_memasukkan", "klub"],
        ascending=[False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    return res


def bentuk_permainan(df: pd.DataFrame, klub: str, n: int = 10) -> list[str]:
    """Hasil n laga terakhir klub ('M', 'S', 'K') urut waktu."""
    laga_klub = df[(df["tim_kandang"] == klub) | (df["tim_tandang"] == klub)].sort_values(
        "tanggal", kind="stable"
    ).tail(n)

    hasil = []
    for row in laga_klub.itertuples():
        if row.tim_kandang == klub:
            res = "M" if row.hasil == "H" else ("S" if row.hasil == "D" else "K")
        else:
            res = "M" if row.hasil == "A" else ("S" if row.hasil == "D" else "K")
        hasil.append(res)
    return hasil


def _daftar_pertemuan(df: pd.DataFrame, klub_a: str, klub_b: str, n: int = 10) -> pd.DataFrame:
    """Daftar pertemuan head-to-head terakhir antara dua klub."""
    sub = df[
        ((df["tim_kandang"] == klub_a) & (df["tim_tandang"] == klub_b))
        | ((df["tim_kandang"] == klub_b) & (df["tim_tandang"] == klub_a))
    ].sort_values("tanggal", kind="stable").tail(n)
    return sub


# ------------------------------------------------------------- potongan HTML

def _tgl(ts: pd.Timestamp) -> str:
    return f"{ts.day} {BULAN[ts.month - 1][:3]} {ts.year}"


def _logo_duel(klub: str) -> str:
    jalur = logo_klub(klub)
    if jalur is None:
        return f'<span class="kode-besar">{escape(singkatan(klub))}</span>'
    return f'<img src="{_uri_logo(str(jalur))}" alt="">'


def _hasil_klub(row, klub: str) -> str:
    if row.hasil == "D":
        return "S"
    return "M" if (row.tim_kandang == klub) == (row.hasil == "H") else "K"


def _duel(df: pd.DataFrame, klub: str, lawan: str, aksen: str) -> str:
    """Kepala navy: dua klub berhadapan, rekor menang-seri-kalah di tengah, batang proporsi di bawah."""
    rekor = rekor_pertemuan(df, klub, lawan)
    status = keadaan_riwayat(rekor["total"])
    warna_lawan = warna_aksen(warna_klub(lawan))
    if warna_lawan == aksen:
        warna_lawan = KABUT
    if status == "kosong":
        angka = '<div class="duel-angka"><div><b>0</b><small>pertemuan</small></div></div>'
        batang = ""
        catatan = '<div class="duel-catatan">Belum pernah bertemu di Premier League.</div>'
    else:
        angka = (
            '<div class="duel-angka">'
            f'<div><b>{angka_hitung(rekor["menang"])}</b>'
            f'<small>{escape(singkatan(klub))} menang</small></div>'
            f'<div><b>{angka_hitung(rekor["seri"], tunda_ms=200)}</b><small>seri</small></div>'
            f'<div><b>{angka_hitung(rekor["kalah"], tunda_ms=280)}</b>'
            f'<small>{escape(singkatan(lawan))} menang</small></div>'
            '</div>'
        )
        bagian = [(rekor["menang"], aksen), (rekor["seri"], "#7FA6B5"), (rekor["kalah"], warna_lawan)]
        batang = '<div class="duel-batang">' + "".join(
            f'<span style="flex:{n};background:{w};--i:{i}"></span>'
            for i, (n, w) in enumerate(bagian) if n > 0
        ) + "</div>"
        if status == "tipis":
            catatan = (f'<div class="duel-catatan peringatan">Baru {rekor["total"]} kali bertemu, '
                       'terlalu sedikit untuk dibaca sebagai pola.</div>')
        else:
            catatan = (f'<div class="duel-catatan">{rekor["total"]} pertemuan di Premier League '
                       'sejak 2000/01.</div>')
    return (
        '<div class="duel"><div class="duel-baris">'
        f'<div class="duel-tim">{_logo_duel(klub)}<div><b>{escape(klub)}</b>'
        '<small>Klub pilihan</small></div></div>'
        f'{angka}'
        f'<div class="duel-tim kanan">{_logo_duel(lawan)}<div><b>{escape(lawan)}</b>'
        '<small>Lawan</small></div></div>'
        f'</div>{batang}{catatan}</div>'
    )


def _lini_pertemuan(df: pd.DataFrame, klub: str, lawan: str) -> str:
    laga = _daftar_pertemuan(df, klub, lawan, 10).iloc[::-1]  # terbaru di atas
    if laga.empty:
        isi = '<div class="kartu-kosong">Belum ada pertemuan untuk ditampilkan.</div>'
    else:
        baris = []
        for i, r in enumerate(laga.itertuples()):
            hasil = _hasil_klub(r, klub)
            baris.append(
                f'<div class="lini-baris" style="--i:{i}"><time>{_tgl(r.tanggal)}</time>'
                f'<div class="tuan"><span>{escape(r.tim_kandang)}</span>{logo_kecil(r.tim_kandang)}</div>'
                f'<span class="lini-skor {hasil}">{int(r.gol_kandang)} - {int(r.gol_tandang)}</span>'
                f'<div class="tamu">{logo_kecil(r.tim_tandang)}<span>{escape(r.tim_tandang)}</span></div>'
                '</div>'
            )
        isi = f'<div class="lini">{"".join(baris)}</div>'
    return (f'<div class="blok" style="--urutan:1"><div class="blok-judul"><b>Pertemuan terakhir</b>'
            f'<span>Sisi {escape(klub)}</span></div>{isi}</div>')


def _blok_bentuk(df: pd.DataFrame, klub: str, lawan: str) -> str:
    baris = []
    for nama in (klub, lawan):
        hasil = bentuk_permainan(df, nama, 10)
        poin = sum(3 if h == "M" else 1 if h == "S" else 0 for h in hasil)
        lencana = "".join(f'<span class="{h}" style="--i:{i}">{h}</span>' for i, h in enumerate(hasil))
        baris.append(
            f'<div class="bentuk-baris"><div class="bentuk-nama">{logo_kecil(nama)}'
            f'<span>{escape(nama)}</span></div><span class="bentuk-poin">{poin} poin</span></div>'
            f'<div class="bentuk">{lencana}</div>'
        )
    return (f'<div class="blok" style="--urutan:2"><div class="blok-judul"><b>Bentuk permainan</b>'
            f'<span>Sepuluh laga terakhir</span></div>{"".join(baris)}'
            '<div class="klasemen-legenda"><span><i style="background:#15803D"></i>M menang</span>'
            '<span><i style="background:#CFD6CC"></i>S seri</span>'
            '<span><i style="background:#A4161A"></i>K kalah</span></div></div>')


def _blok_klasemen(df: pd.DataFrame, klub: str, lawan: str, aksen: str) -> str:
    papan = klasemen(df, MUSIM_BERJALAN)
    akhir = df.loc[df["musim"] == MUSIM_BERJALAN, "tanggal"].max()
    n = len(papan)
    baris = []
    for i, r in enumerate(papan.itertuples(), start=1):
        kelas = []
        if i <= 4:
            kelas.append("eropa")
        if i > n - 3:
            kelas.append("degradasi")
        if r.klub == klub:
            kelas.append("saya")
        gaya = f"--i:{i};--aksen:{aksen}" if r.klub == klub else f"--i:{i}"
        nama = escape(r.klub) + (' <small class="keterangan">lawan</small>' if r.klub == lawan else "")
        baris.append(
            f'<tr class="{" ".join(kelas)}" style="{gaya}">'
            f'<td class="pos kiri"><span>{i}</span></td>'
            f'<td class="klub kiri"><span class="klub-isi">{logo_kecil(r.klub)}<span>{nama}</span></span></td>'
            f'<td>{r.main}</td><td>{r.menang}</td><td>{r.seri}</td><td>{r.kalah}</td>'
            f'<td>{r.gol_memasukkan}</td><td>{r.gol_kemasukan}</td><td>{r.selisih:+d}</td>'
            f'<td class="poin">{r.poin}</td></tr>'
        )
    kepala = "".join(f"<th>{h}</th>" for h in ["Main", "M", "S", "K", "GM", "GK", "SG", "Poin"])
    return (
        f'<div class="blok" style="--urutan:3"><div class="blok-judul"><b>Klasemen {MUSIM_BERJALAN}</b>'
        f'<span>Sampai {akhir.day} {BULAN[akhir.month - 1]} {akhir.year}</span></div>'
        '<table class="klasemen"><thead><tr><th class="kiri">Pos</th><th class="kiri">Klub</th>'
        f'{kepala}</tr></thead><tbody>{"".join(baris)}</tbody></table>'
        '<div class="klasemen-legenda"><span><i style="background:#157D7B"></i>Empat besar</span>'
        '<span><i style="background:#A4161A"></i>Zona degradasi</span></div></div>'
    )


def tampil() -> None:
    df = muat_pertandingan(str(JALUR_DATA))
    semua_klub = klub_musim(df, MUSIM_BERJALAN)
    if st.session_state.get("hist_klub") not in semua_klub:
        bawaan = st.session_state.get("klub", "Arsenal")
        st.session_state["hist_klub"] = bawaan if bawaan in semua_klub else semua_klub[0]

    kol_judul, kol_klub, kol_lawan = st.columns([3, 1.3, 1.3], vertical_alignment="top")
    with kol_judul:
        st.markdown(
            '<div class="kepala-hal"><div><h2>History</h2>'
            '<p>Rekor pertemuan dua klub, bentuk terkini, dan klasemen musim berjalan.</p></div></div>',
            unsafe_allow_html=True,
        )
    with kol_klub:
        klub = st.selectbox("Klub", semua_klub, key="hist_klub")
    daftar_lawan = [k for k in semua_klub if k != klub]
    if st.session_state.get("history_lawan") not in daftar_lawan:
        st.session_state["history_lawan"] = daftar_lawan[0]
    with kol_lawan:
        lawan = st.selectbox("Lawan", daftar_lawan, key="history_lawan")
    aksen = warna_aksen(warna_klub(klub))

    st.markdown(_duel(df, klub, lawan, aksen), unsafe_allow_html=True)
    with st.container(key="hist-grid"):
        kol_a, kol_b = st.columns([1.25, 1])
        with kol_a:
            st.markdown(_lini_pertemuan(df, klub, lawan), unsafe_allow_html=True)
        with kol_b:
            st.markdown(_blok_bentuk(df, klub, lawan), unsafe_allow_html=True)
    st.markdown(_blok_klasemen(df, klub, lawan, aksen), unsafe_allow_html=True)
