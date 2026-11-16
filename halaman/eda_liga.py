"""Halaman EDA Liga: antarmuka 2-kolom bergaya SofaScore.

Kolom Kiri: Riwayat pertandingan (Match List) dengan filter musim dan klub.
Kolom Kanan: Tampilan statistik pertandingan lengkap (SofaScore comparison bars)
             dan analisis makro tren liga 27 musim (Rubrik UAS PDS).
"""
from html import escape
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from gaya.komponen import GARIS, grafik_dasar, warna_aksen
from inti.data import klub_musim, muat_pertandingan
from inti.klub import logo_klub, singkatan, warna_klub
from inti.sesi import BULAN, JALUR_DATA

BAGIAN = [
    {
        "id": "distribusi_gol",
        "judul": "Lebih dari separuh pertandingan berakhir dengan dua gol atau kurang",
        "pertanyaan": "Berapa gol yang wajar?",
        "kolom_syarat": None,
    },
    {
        "id": "keuntungan_kandang",
        "judul": "Keunggulan bermain di kandang relatif stabil di kisaran 45 persen kemenangan",
        "pertanyaan": "Seberapa nyata keuntungan main di kandang?",
        "kolom_syarat": None,
    },
    {
        "id": "tembakan_vs_gol",
        "judul": "Akurasi tembakan tepat sasaran jauh lebih menentukan raihan gol daripada kuantitas tembakan",
        "pertanyaan": "Apakah menembak banyak berarti menang?",
        "kolom_syarat": None,
    },
    {
        "id": "waktu_gol",
        "judul": "Mayoritas gol tercipta pada babak kedua seiring intensitas dan penurunan stamina",
        "pertanyaan": "Kapan gol terjadi?",
        "kolom_syarat": None,
    },
    {
        "id": "disiplin",
        "judul": "Akumulasi pelanggaran tidak berbanding lurus dengan kekalahan, tetapi kartu merah sangat menentukan",
        "pertanyaan": "Apakah disiplin berpengaruh?",
        "kolom_syarat": None,
    },
    {
        "id": "konsistensi",
        "judul": "Hanya segelintir klub papan atas yang mampu konsisten meraih di atas dua poin per laga",
        "pertanyaan": "Siapa yang konsisten?",
        "kolom_syarat": None,
    },
    {
        "id": "penguasaan_bola",
        "judul": "Dominasi penguasaan bola tidak selalu menjamin konversi gol tanpa penetrasi efektif",
        "pertanyaan": "Apakah menguasai bola berarti menang?",
        "kolom_syarat": "penguasaan_bola_kandang",
    },
    {
        "id": "peluang_xg",
        "judul": "Kualitas peluang yang diciptakan berkorelasi sangat kuat dengan probabilitas kemenangan",
        "pertanyaan": "Seberapa dekat gol dengan peluang yang diciptakan?",
        "kolom_syarat": "xg_api_kandang",
    },
]


def cukup_lengkap(df: pd.DataFrame, kolom: str, ambang: float = 0.6) -> bool:
    """Cek apakah kolom memiliki cakupan data terisi minimal sebesar ambang (default 60%)."""
    if kolom not in df.columns:
        return False
    return bool(df[kolom].notna().mean() >= ambang)


def tren_per_musim(df: pd.DataFrame, metrik: str) -> pd.DataFrame:
    """Menghitung agregat metrik per musim yang selalu dinormalkan per laga."""
    baris = []
    musim_list = sorted(df["musim"].unique(), key=lambda m: str(m))
    for m in musim_list:
        sub = df[df["musim"] == m]
        n_laga = len(sub)
        if n_laga == 0:
            continue
        if metrik == "poin":
            # Rata-rata poin total yang diperebutkan per laga (menang = 3, seri = 2)
            pts = np.where(sub["hasil"] == "D", 2.0, 3.0)
            nilai = float(pts.mean())
        elif metrik == "menang_kandang":
            nilai = float((sub["hasil"] == "H").mean())
        elif metrik == "gol":
            nilai = float((sub["gol_kandang"] + sub["gol_tandang"]).mean())
        elif metrik == "gol_babak1":
            nilai = float((sub["gol_kandang_babak1"] + sub["gol_tandang_babak1"]).mean())
        elif metrik in sub.columns:
            nilai = float(sub[metrik].mean())
        else:
            nilai = 0.0
        baris.append({"musim": m, "nilai": nilai, "jumlah_laga": n_laga})
    return pd.DataFrame(baris)


def _poin_per_klub_per_musim(df: pd.DataFrame) -> pd.DataFrame:
    """Rata-rata poin per laga untuk tiap klub per musim."""
    baris = []
    for (musim, klub), sub in df.groupby(["musim", "tim_kandang"]):
        pk = np.where(sub["hasil"] == "H", 3, np.where(sub["hasil"] == "D", 1, 0))
        baris.append({"musim": musim, "klub": klub, "main": len(sub), "poin": pk.sum()})
    for (musim, klub), sub in df.groupby(["musim", "tim_tandang"]):
        pt = np.where(sub["hasil"] == "A", 3, np.where(sub["hasil"] == "D", 1, 0))
        baris.append({"musim": musim, "klub": klub, "main": len(sub), "poin": pt.sum()})

    temp = pd.DataFrame(baris)
    agg = temp.groupby(["musim", "klub"], as_index=False).sum()
    agg["poin_per_laga"] = agg["poin"] / agg["main"]
    return agg


def _format_tanggal(ts: pd.Timestamp) -> str:
    return f"{ts.day} {BULAN[ts.month - 1]} {ts.year}"


def _bar_sofascore(nama_stat: str, val_k: float, val_t: float, format_fmt: str = "{:.0f}",
                   aksen_k: str = "#EF0107", aksen_t: str = "#0057B8") -> str:
    """Render satu baris bar perbandingan dua tim gaya SofaScore."""
    total = val_k + val_t
    if total > 0:
        pct_k = max(8.0, min(92.0, (val_k / total) * 100.0))
        pct_t = 100.0 - pct_k
    else:
        pct_k, pct_t = 50.0, 50.0

    teks_k = format_fmt.format(val_k)
    teks_t = format_fmt.format(val_t)

    bold_k = "font-weight: 700;" if val_k >= val_t else "color: var(--teks-2);"
    bold_t = "font-weight: 700;" if val_t >= val_k else "color: var(--teks-2);"

    return (
        '<div style="margin-bottom: 14px;">'
        '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; font-size: 13px;">'
        f'<span style="font-family: var(--huruf-sempit); {bold_k} font-size: 15px; width: 45px; text-align: left;">{teks_k}</span>'
        f'<span style="color: var(--teks-2); font-size: 13px; text-align: center; flex: 1;">{escape(nama_stat)}</span>'
        f'<span style="font-family: var(--huruf-sempit); {bold_t} font-size: 15px; width: 45px; text-align: right;">{teks_t}</span>'
        '</div>'
        '<div style="display: flex; height: 6px; background: var(--garis); border-radius: 3px; overflow: hidden; gap: 2px;">'
        f'<div style="width: {pct_k:.1f}%; background: {aksen_k}; border-radius: 3px 0 0 3px;"></div>'
        f'<div style="width: {pct_t:.1f}%; background: {aksen_t}; border-radius: 0 3px 3px 0;"></div>'
        '</div>'
        '</div>'
    )


def tampil() -> None:
    df = muat_pertandingan(str(JALUR_DATA))
    klub_terpilih = st.session_state.get("klub", "Arsenal")
    aksen = warna_aksen(warna_klub(klub_terpilih))

    st.markdown(
        '<div style="font-size: 13px; color: var(--teks-2); margin-bottom: 4px;">'
        'Eksplorasi Statistik Pertandingan & Analisis Liga (Gaya SofaScore)'
        '</div>',
        unsafe_allow_html=True,
    )

    # Layout 2 Kolom: Kiri = Riwayat Laga, Kanan = Statistik Laga & Tren Liga
    col_kiri, col_kanan = st.columns([1, 1.85], gap="large")

    # ─────────────────────────────────────────────────────────────
    # KOLOM KIRI: HISTORY MATCHES (DAFTAR PERTANDINGAN GAYA SOFASCORE)
    # ─────────────────────────────────────────────────────────────
    with col_kiri:
        st.markdown(
            '<div style="border-bottom: 1px solid var(--garis); padding-bottom: 8px; margin-bottom: 12px;">'
            '<h3 style="margin: 0; font-size: 18px;">Pertandingan</h3>'
            '</div>',
            unsafe_allow_html=True,
        )

        semua_musim = sorted(df["musim"].unique(), reverse=True)
        musim_dipilih = st.selectbox("Musim", semua_musim, index=0, key="sofa_musim")

        klub_musim_ini = ["Semua Klub"] + klub_musim(df, musim_dipilih)
        default_klub_idx = klub_musim_ini.index(klub_terpilih) if klub_terpilih in klub_musim_ini else 0
        klub_filter = st.selectbox("Filter Klub", klub_musim_ini, index=default_klub_idx, key="sofa_klub_filter")

        df_musim = df[df["musim"] == musim_dipilih]
        if klub_filter != "Semua Klub":
            laga_list_df = df_musim[
                (df_musim["tim_kandang"] == klub_filter) | (df_musim["tim_tandang"] == klub_filter)
            ].sort_values("tanggal", ascending=False)
        else:
            laga_list_df = df_musim.sort_values("tanggal", ascending=False)

        total_ditemukan = len(laga_list_df)
        st.caption(f"Menampilkan {total_ditemukan} pertandingan")

        if laga_list_df.empty:
            st.info("Tidak ada data pertandingan untuk filter ini.")
            selected_match_id = None
        else:
            opsi_laga = []
            id_list = []
            for r in laga_list_df.itertuples():
                tgl_pendek = r.tanggal.strftime("%d/%m")
                label = f"{tgl_pendek} · {singkatan(r.tim_kandang)} {r.gol_kandang} - {r.gol_tandang} {singkatan(r.tim_tandang)}"
                opsi_laga.append(label)
                id_list.append(r.Index)

            idx_pilihan = st.selectbox(
                "Pilih Laga untuk Melihat Statistik:",
                range(len(opsi_laga)),
                format_func=lambda i: opsi_laga[i],
                key="sofa_laga_pilihan",
            )
            selected_match_id = id_list[idx_pilihan]

            # Preview List 6 Laga Terkini (Visual SofaScore)
            st.markdown(
                '<div style="margin-top: 16px; margin-bottom: 8px; font-size: 13px; color: var(--teks-2); font-weight: 500;">'
                'Jadwal & Hasil Terbaru:'
                '</div>',
                unsafe_allow_html=True,
            )
            preview_laga = laga_list_df.head(8)
            cards_html = []
            for r in preview_laga.itertuples():
                is_selected = (r.Index == selected_match_id)
                border_style = f"border-left: 3px solid {aksen}; background: #FFFFFF;" if is_selected else "background: var(--permukaan);"
                tgl_str = r.tanggal.strftime("%d %b %Y")
                skor_str = f"{r.gol_kandang} - {r.gol_tandang}"
                cards_html.append(
                    f'<div style="border: 1px solid var(--garis); border-radius: 4px; padding: 8px 10px; margin-bottom: 6px; {border_style} font-size: 13px;">'
                    f'<div style="display: flex; justify-content: space-between; color: var(--teks-2); font-size: 11px; margin-bottom: 4px;">'
                    f'<span>{tgl_str}</span><span style="font-weight: 600; color: var(--teks);">FT</span>'
                    f'</div>'
                    f'<div style="display: flex; justify-content: space-between; align-items: center;">'
                    f'<div style="flex: 1;">'
                    f'<div>{escape(r.tim_kandang)}</div>'
                    f'<div>{escape(r.tim_tandang)}</div>'
                    f'</div>'
                    f'<div style="font-family: var(--huruf-sempit); font-size: 15px; font-weight: 700; text-align: right; width: 35px;">'
                    f'<div>{r.gol_kandang}</div><div>{r.gol_tandang}</div>'
                    f'</div>'
                    f'</div>'
                    f'</div>'
                )
            st.markdown("".join(cards_html), unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────
    # KOLOM KANAN: STATISTIK PERTANDINGAN LENGKAP & ANALISIS LIGA
    # ─────────────────────────────────────────────────────────────
    with col_kanan:
        tab_stat, tab_liga = st.tabs(["Statistik Pertandingan (SofaScore)", "Tren & Pola Liga (27 Musim)"])

        with tab_stat:
            if selected_match_id is not None:
                laga_row = df.loc[selected_match_id]
                tim_k = laga_row["tim_kandang"]
                tim_t = laga_row["tim_tandang"]
                aksen_k = warna_aksen(warna_klub(tim_k))
                aksen_t = warna_aksen(warna_klub(tim_t))
                tgl_laga = laga_row["tanggal"]

                # SofaScore Header Banner
                wasit_str = f" · Wasit: {escape(str(laga_row['wasit']))}" if pd.notna(laga_row.get("wasit")) else ""
                stadion_str = f" · Stadion: {escape(str(laga_row['stadion']))}" if pd.notna(laga_row.get("stadion")) else ""
                banner_html = (
                    '<div class="panel" style="margin-bottom: 20px; text-align: center; border-radius: 6px; padding: 20px;">'
                    f'<div style="font-size: 13px; color: var(--teks-2); margin-bottom: 8px;">{_format_tanggal(tgl_laga)} · Premier League</div>'
                    '<div style="display: grid; grid-template-columns: 1fr 120px 1fr; align-items: center;">'
                    f'<div style="text-align: right; padding-right: 16px;">'
                    f'<div style="font-size: 18px; font-weight: 600; color: {aksen_k};">{escape(tim_k)}</div>'
                    f'<div class="keterangan">{singkatan(tim_k)} (Kandang)</div>'
                    '</div>'
                    '<div style="background: var(--latar); border: 1px solid var(--garis); border-radius: 4px; padding: 8px 12px;">'
                    f'<div style="font-family: var(--huruf-sempit); font-size: 32px; font-weight: 700; line-height: 1;">'
                    f'{int(laga_row["gol_kandang"])} : {int(laga_row["gol_tandang"])}'
                    '</div>'
                    '<div style="font-size: 11px; font-weight: 600; color: var(--teks-2); margin-top: 4px;">SELESAI (FT)</div>'
                    '</div>'
                    f'<div style="text-align: left; padding-left: 16px;">'
                    f'<div style="font-size: 18px; font-weight: 600; color: {aksen_t};">{escape(tim_t)}</div>'
                    f'<div class="keterangan">{singkatan(tim_t)} (Tandang)</div>'
                    '</div>'
                    '</div>'
                    f'<div style="margin-top: 12px; font-size: 12px; color: var(--teks-2);">'
                    f'Babak 1 (HT): {int(laga_row.get("gol_kandang_babak1", 0))} - {int(laga_row.get("gol_tandang_babak1", 0))}'
                    f'{wasit_str}{stadion_str}'
                    '</div>'
                    '</div>'
                )
                st.markdown(banner_html, unsafe_allow_html=True)

                st.markdown('<h3 style="font-size: 16px; margin: 16px 0 12px;">Statistik Pertandingan</h3>', unsafe_allow_html=True)

                # SofaScore Comparison Bars
                bars_html = []

                # xG jika tersedia
                if pd.notna(laga_row.get("xg_kandang")) and pd.notna(laga_row.get("xg_tandang")):
                    bars_html.append(_bar_sofascore("Gol yang Diharapkan (xG)", float(laga_row["xg_kandang"]), float(laga_row["xg_tandang"]), "{:.2f}", aksen_k, aksen_t))
                elif pd.notna(laga_row.get("xg_api_kandang")) and pd.notna(laga_row.get("xg_api_tandang")):
                    bars_html.append(_bar_sofascore("Gol yang Diharapkan (xG API)", float(laga_row["xg_api_kandang"]), float(laga_row["xg_api_tandang"]), "{:.2f}", aksen_k, aksen_t))

                # Penguasaan bola jika tersedia
                if pd.notna(laga_row.get("penguasaan_bola_kandang")) and pd.notna(laga_row.get("penguasaan_bola_tandang")):
                    bars_html.append(_bar_sofascore("Penguasaan Bola (%)", float(laga_row["penguasaan_bola_kandang"]), float(laga_row["penguasaan_bola_tandang"]), "{:.0f}%", aksen_k, aksen_t))

                # Statistik Dasar Pertandingan
                bars_html.append(_bar_sofascore("Total Tembakan", float(laga_row["tembakan_kandang"]), float(laga_row["tembakan_tandang"]), "{:.0f}", aksen_k, aksen_t))
                bars_html.append(_bar_sofascore("Tembakan Tepat Sasaran", float(laga_row["tembakan_tepat_kandang"]), float(laga_row["tembakan_tepat_tandang"]), "{:.0f}", aksen_k, aksen_t))

                tot_k = max(1.0, float(laga_row["tembakan_kandang"]))
                tot_t = max(1.0, float(laga_row["tembakan_tandang"]))
                acc_k = (float(laga_row["tembakan_tepat_kandang"]) / tot_k) * 100.0
                acc_t = (float(laga_row["tembakan_tepat_tandang"]) / tot_t) * 100.0
                bars_html.append(_bar_sofascore("Akurasi Tembakan", acc_k, acc_t, "{:.1f}%", aksen_k, aksen_t))

                bars_html.append(_bar_sofascore("Sepak Pojok", float(laga_row["sepak_pojok_kandang"]), float(laga_row["sepak_pojok_tandang"]), "{:.0f}", aksen_k, aksen_t))
                bars_html.append(_bar_sofascore("Pelanggaran", float(laga_row["pelanggaran_kandang"]), float(laga_row["pelanggaran_tandang"]), "{:.0f}", aksen_k, aksen_t))
                bars_html.append(_bar_sofascore("Kartu Kuning", float(laga_row["kartu_kuning_kandang"]), float(laga_row["kartu_kuning_tandang"]), "{:.0f}", aksen_k, aksen_t))
                bars_html.append(_bar_sofascore("Kartu Merah", float(laga_row["kartu_merah_kandang"]), float(laga_row["kartu_merah_tandang"]), "{:.0f}", aksen_k, aksen_t))

                # Umpan jika tersedia
                if pd.notna(laga_row.get("umpan_kandang")) and pd.notna(laga_row.get("umpan_tandang")):
                    bars_html.append(_bar_sofascore("Jumlah Umpan", float(laga_row["umpan_kandang"]), float(laga_row["umpan_tandang"]), "{:.0f}", aksen_k, aksen_t))

                st.markdown(
                    f'<div class="panel" style="padding: 18px 20px;">{"".join(bars_html)}</div>',
                    unsafe_allow_html=True,
                )

                # Odds Pasar jika tersedia
                if pd.notna(laga_row.get("odds_kandang")) and pd.notna(laga_row.get("odds_tandang")):
                    st.markdown('<div class="dalam"><small class="keterangan">Odds Pasar Taruhan Sebelum Laga</small></div>', unsafe_allow_html=True)
                    c_od1, c_od2, c_od3 = st.columns(3)
                    with c_od1:
                        st.markdown(
                            f'<div class="panel" style="text-align: center;"><div class="keterangan">{escape(tim_k)}</div>'
                            f'<div class="angka" style="font-size: 18px; font-weight: 600;">{laga_row["odds_kandang"]:.2f}</div></div>',
                            unsafe_allow_html=True,
                        )
                    with c_od2:
                        st.markdown(
                            f'<div class="panel" style="text-align: center;"><div class="keterangan">Seri</div>'
                            f'<div class="angka" style="font-size: 18px; font-weight: 600;">{laga_row["odds_seri"]:.2f}</div></div>',
                            unsafe_allow_html=True,
                        )
                    with c_od3:
                        st.markdown(
                            f'<div class="panel" style="text-align: center;"><div class="keterangan">{escape(tim_t)}</div>'
                            f'<div class="angka" style="font-size: 18px; font-weight: 600;">{laga_row["odds_tandang"]:.2f}</div></div>',
                            unsafe_allow_html=True,
                        )

        # TAB 2: TREN & POLA MAKRO LIGA (RUBRIK UAS 3 & SPEC 6.4)
        with tab_liga:
            st.markdown(
                '<p style="max-width: 68ch; font-size: 14px; line-height: 1.6; color: var(--teks-2); margin-bottom: 16px;">'
                'Enam visualisasi temuan makro 27 musim Liga Inggris untuk menjawab pertanyaan krusial pelatih.'
                '</p>',
                unsafe_allow_html=True,
            )

            df_sub = df[df["musim"] == musim_dipilih].copy() if musim_dipilih else df.copy()

            for b in BAGIAN:
                syarat = b["kolom_syarat"]
                if syarat is not None and not cukup_lengkap(df, syarat):
                    continue

                st.markdown(f'<div style="margin-top: 24px;"><small class="keterangan">{b["pertanyaan"]}</small></div>', unsafe_allow_html=True)

                if b["id"] == "distribusi_gol":
                    total_gol = (df["gol_kandang"] + df["gol_tandang"]).clip(upper=7)
                    dist = total_gol.value_counts(normalize=True).sort_index().reset_index()
                    dist.columns = ["total_gol", "persen"]
                    dist["persen"] = dist["persen"] * 100
                    dist["gol_label"] = dist["total_gol"].apply(lambda g: f"{g}+" if g == 7 else str(g))

                    chart = alt.Chart(dist).mark_bar(color=aksen, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                        x=alt.X("gol_label:O", title="Total gol dalam pertandingan", sort=None, axis=alt.Axis(grid=False)),
                        y=alt.Y("persen:Q", title="Persentase (%)", axis=alt.Axis(grid=True)),
                        tooltip=["gol_label", alt.Tooltip("persen:Q", format=".1f")],
                    ).properties(title=b["judul"], height=220).configure_title(
                        font="IBM Plex Sans", fontSize=15, fontWeight=600, color="#0E1F18", anchor="start"
                    ).configure_axis(
                        domain=False, ticks=False, labelColor="#65736C", titleColor="#65736C",
                        labelFont="IBM Plex Sans Condensed", titleFont="IBM Plex Sans",
                        labelFontSize=12, titleFontSize=12
                    ).configure_axisY(gridColor=GARIS, gridWidth=1)
                    st.altair_chart(chart, use_container_width=True)

                elif b["id"] == "keuntungan_kandang":
                    t = tren_per_musim(df, "menang_kandang")
                    t["nilai"] = t["nilai"] * 100
                    t["seri"] = "Liga"
                    chart = grafik_dasar(
                        t, x="musim", y="nilai", judul=b["judul"], sorot="Liga",
                        aksen=aksen, seri="seri", label_x="Musim", label_y="Menang Kandang (%)"
                    ).properties(height=220)
                    st.altair_chart(chart, use_container_width=True)

                elif b["id"] == "tembakan_vs_gol":
                    t_tembakan = df.groupby("musim")[["tembakan_kandang", "gol_kandang"]].mean().reset_index()
                    t_tembakan["seri"] = "Rata-rata Tembakan"
                    t_tembakan["nilai"] = t_tembakan["tembakan_kandang"]
                    chart = grafik_dasar(
                        t_tembakan, x="musim", y="nilai", judul=b["judul"], sorot="Rata-rata Tembakan",
                        aksen=aksen, seri="seri", label_x="Musim", label_y="Tembakan per laga"
                    ).properties(height=220)
                    st.altair_chart(chart, use_container_width=True)

                elif b["id"] == "waktu_gol":
                    t_b1 = tren_per_musim(df, "gol_babak1")
                    t_b2 = tren_per_musim(df, "gol")
                    t_b2["nilai"] = t_b2["nilai"] - t_b1["nilai"]
                    t_b1["seri"] = "Babak Pertama"
                    t_b2["seri"] = "Babak Kedua"
                    t_waktu = pd.concat([t_b1, t_b2])
                    chart = grafik_dasar(
                        t_waktu, x="musim", y="nilai", judul=b["judul"], sorot="Babak Kedua",
                        aksen=aksen, seri="seri", label_x="Musim", label_y="Gol per laga"
                    ).properties(height=220)
                    st.altair_chart(chart, use_container_width=True)

                elif b["id"] == "disiplin":
                    df["kartu_kuning"] = df["kartu_kuning_kandang"] + df["kartu_kuning_tandang"]
                    t_kartu = df.groupby("musim")["kartu_kuning"].mean().reset_index()
                    t_kartu["seri"] = "Kartu Kuning"
                    t_kartu["nilai"] = t_kartu["kartu_kuning"]
                    chart = grafik_dasar(
                        t_kartu, x="musim", y="nilai", judul=b["judul"], sorot="Kartu Kuning",
                        aksen=aksen, seri="seri", label_x="Musim", label_y="Kartu per laga"
                    ).properties(height=220)
                    st.altair_chart(chart, use_container_width=True)

                elif b["id"] == "konsistensi":
                    pk_df = _poin_per_klub_per_musim(df)
                    chart = grafik_dasar(
                        pk_df, x="musim", y="poin_per_laga", judul=b["judul"], sorot=klub_terpilih,
                        aksen=aksen, seri="klub", label_x="Musim", label_y="Poin per laga"
                    ).properties(height=250)
                    st.altair_chart(chart, use_container_width=True)
