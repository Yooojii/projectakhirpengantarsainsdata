"""Halaman History: rekor pertemuan historis, bentuk permainan, dan klasemen."""
from html import escape
import pandas as pd
import streamlit as st

from gaya.komponen import warna_aksen
from inti.data import klub_musim, muat_pertandingan
from inti.klub import singkatan, warna_klub
from inti.sesi import BULAN, JALUR_DATA


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


def tampil() -> None:
    df = muat_pertandingan(str(JALUR_DATA))
    klub_saya = st.session_state.get("klub", "Arsenal")
    aksen = warna_aksen(warna_klub(klub_saya))

    semua_klub = klub_musim(df, "2026/27")
    daftar_lawan = [k for k in semua_klub if k != klub_saya]

    st.markdown('<div class="bagian"><h3>Riwayat Pertemuan & Klasemen</h3></div>', unsafe_allow_html=True)

    # 1. Pemilih lawan (19 klub lain musim berjalan)
    lawan = st.selectbox("Pilih Lawan", daftar_lawan, key="history_lawan")

    # 2. Rekor pertemuan
    rekor = rekor_pertemuan(df, klub_saya, lawan)
    status = keadaan_riwayat(rekor["total"])

    st.markdown(f'<div class="bagian"><small class="keterangan">Rekor Pertemuan: {escape(klub_saya)} vs {escape(lawan)}</small></div>', unsafe_allow_html=True)

    if status == "kosong":
        st.markdown(
            '<div class="panel" style="margin-top: 12px; margin-bottom: 24px;">'
            '<p style="font-size: 16px; color: var(--teks); margin: 0;">'
            'Belum pernah bertemu di Liga Inggris.'
            '</p></div>',
            unsafe_allow_html=True,
        )
    else:
        if status == "tipis":
            st.markdown(
                f'<div class="risiko-peringatan" style="color: var(--peringatan); font-size: 14px; font-weight: 500; margin-bottom: 16px;">'
                f'Baru {rekor["total"]} kali bertemu. Terlalu sedikit untuk jadi pola.'
                '</div>',
                unsafe_allow_html=True,
            )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                f'<div class="panel"><div class="keterangan">{escape(klub_saya)} Menang</div>'
                f'<div class="angka" style="font-size: 24px; font-weight: 600; color: {aksen};">{rekor["menang"]}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="panel"><div class="keterangan">Seri</div>'
                f'<div class="angka" style="font-size: 24px; font-weight: 600;">{rekor["seri"]}</div></div>',
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f'<div class="panel"><div class="keterangan">{escape(lawan)} Menang</div>'
                f'<div class="angka" style="font-size: 24px; font-weight: 600;">{rekor["kalah"]}</div></div>',
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                f'<div class="panel"><div class="keterangan">Total Laga</div>'
                f'<div class="angka" style="font-size: 24px; font-weight: 600;">{rekor["total"]}</div></div>',
                unsafe_allow_html=True,
            )

        # 3. Sepuluh pertemuan terakhir
        st.markdown('<div class="dalam"><small class="keterangan">Sepuluh Pertemuan Terakhir</small></div>', unsafe_allow_html=True)
        laga_h2h = _daftar_pertemuan(df, klub_saya, lawan, 10)
        baris_h2h = []
        for row in laga_h2h.itertuples():
            tgl = row.tanggal
            tgl_str = f"{tgl.day} {BULAN[tgl.month - 1]} {tgl.year}"
            skor_str = f"{row.gol_kandang} - {row.gol_tandang}"
            # Titik penanda hasil klub saya
            if row.tim_kandang == klub_saya:
                res = "M" if row.hasil == "H" else ("S" if row.hasil == "D" else "K")
            else:
                res = "M" if row.hasil == "A" else ("S" if row.hasil == "D" else "K")

            warna_titik = aksen if res == "M" else ("var(--garis)" if res == "S" else "var(--bahaya)")
            dot = f'<span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: {warna_titik}; margin-right: 8px;"></span>'

            baris_h2h.append(
                f'<tr>'
                f'<td class="teks" style="font-size: 13px; color: var(--teks-2);">{dot}{tgl_str}</td>'
                f'<td class="teks">{escape(singkatan(row.tim_kandang))}</td>'
                f'<td style="font-weight: 600; text-align: center;">{skor_str}</td>'
                f'<td class="teks">{escape(singkatan(row.tim_tandang))}</td>'
                f'</tr>'
            )

        st.markdown(
            '<table class="tabel" style="width: 100%; margin-top: 8px; margin-bottom: 24px;">'
            '<thead><tr>'
            '<th class="teks">Tanggal</th>'
            '<th class="teks">Tuan Rumah</th>'
            '<th style="text-align: center;">Skor</th>'
            '<th class="teks">Tamu</th>'
            '</tr></thead>'
            f'<tbody>{"".join(baris_h2h)}</tbody>'
            '</table>',
            unsafe_allow_html=True,
        )

    # 4. Bentuk Permainan
    st.markdown('<div class="bagian"><small class="keterangan">Bentuk Permainan (Sepuluh Laga Terakhir)</small></div>', unsafe_allow_html=True)
    b_saya = bentuk_permainan(df, klub_saya, 10)
    b_lawan = bentuk_permainan(df, lawan, 10)

    def _render_bentuk(nama, hasil_list, is_saya):
        badges = []
        for r in hasil_list:
            if r == "M":
                bg = aksen if is_saya else "var(--teks)"
                color = "#FFFFFF"
            elif r == "S":
                bg = "var(--garis)"
                color = "var(--teks)"
            else:
                bg = "var(--bahaya)"
                color = "#FFFFFF"
            badges.append(
                f'<span style="display: inline-block; width: 24px; height: 24px; line-height: 24px; '
                f'text-align: center; border-radius: 4px; background: {bg}; color: {color}; '
                f'font-family: var(--huruf-sempit); font-size: 12px; font-weight: 600; margin-right: 4px;">{r}</span>'
            )
        return (
            f'<div class="panel" style="margin-top: 8px;">'
            f'<div class="keterangan" style="margin-bottom: 6px;">{escape(nama)}</div>'
            f'<div>{"".join(badges)}</div>'
            f'</div>'
        )

    col_b1, col_b2 = st.columns(2)
    with col_b1:
        st.markdown(_render_bentuk(klub_saya, b_saya, True), unsafe_allow_html=True)
    with col_b2:
        st.markdown(_render_bentuk(lawan, b_lawan, False), unsafe_allow_html=True)

    # 5. Klasemen Musim Berjalan
    st.markdown(
        '<div class="bagian"><small class="keterangan">Klasemen sampai 2 November 2026</small></div>',
        unsafe_allow_html=True,
    )
    klasemen_df = klasemen(df, "2026/27")

    baris_klasemen = []
    for idx, row in enumerate(klasemen_df.itertuples(), start=1):
        terpilih = row.klub == klub_saya
        style_row = f'background: {aksen}15; font-weight: 600;' if terpilih else ''
        teks_color = f'color: {aksen};' if terpilih else ''
        baris_klasemen.append(
            f'<tr style="{style_row}">'
            f'<td style="text-align: center; {teks_color}">{idx}</td>'
            f'<td class="teks" style="{teks_color}">{escape(row.klub)}</td>'
            f'<td>{row.main}</td>'
            f'<td>{row.menang}</td>'
            f'<td>{row.seri}</td>'
            f'<td>{row.kalah}</td>'
            f'<td>{row.gol_memasukkan}</td>'
            f'<td>{row.gol_kemasukan}</td>'
            f'<td>{row.selisih:+d}</td>'
            f'<td style="font-weight: 700; {teks_color}">{row.poin}</td>'
            f'</tr>'
        )

    st.markdown(
        '<table class="tabel" style="width: 100%; margin-top: 12px;">'
        '<thead><tr>'
        '<th style="text-align: center;">Pos</th>'
        '<th class="teks">Klub</th>'
        '<th>Main</th>'
        '<th>M</th>'
        '<th>S</th>'
        '<th>K</th>'
        '<th>GM</th>'
        '<th>GK</th>'
        '<th>SG</th>'
        '<th>Poin</th>'
        '</tr></thead>'
        f'<tbody>{"".join(baris_klasemen)}</tbody>'
        '</table>',
        unsafe_allow_html=True,
    )
