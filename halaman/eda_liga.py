"""Halaman EDA Liga: eksplorasi pola kompetisi 27 musim Liga Inggris."""
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from gaya.komponen import GARIS, grafik_dasar, warna_aksen
from inti.data import muat_pertandingan
from inti.klub import warna_klub
from inti.sesi import JALUR_DATA

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


def tampil() -> None:
    df = muat_pertandingan(str(JALUR_DATA))
    klub = st.session_state.get("klub", "Arsenal")
    aksen = warna_aksen(warna_klub(klub))

    st.markdown('<div class="bagian"><h3>Eksplorasi Data Liga Inggris (2000–2026)</h3></div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="max-width: 68ch; font-size: 16px; line-height: 1.6; color: var(--teks-2);">'
        'Analisis empiris atas 9.880 pertandingan melintasi 27 musim. Semua metrik disajikan '
        'dalam ukuran per laga untuk menjaga konsistensi terhadap musim yang tidak utuh.'
        '</p>',
        unsafe_allow_html=True,
    )

    semua_musim = sorted(df["musim"].unique())
    rentang = st.select_slider(
        "Rentang Musim",
        options=semua_musim,
        value=(semua_musim[0], semua_musim[-1]),
    )
    m_awal, m_akhir = rentang
    idx_awal = semua_musim.index(m_awal)
    idx_akhir = semua_musim.index(m_akhir)
    musim_terpilih = semua_musim[idx_awal:idx_akhir + 1]
    df_sub = df[df["musim"].isin(musim_terpilih)].copy()

    catatan_tidak_utuh = any(m in musim_terpilih for m in ["2003/04", "2004/05", "2026/27"])

    for b in BAGIAN:
        syarat = b["kolom_syarat"]
        if syarat is not None and not cukup_lengkap(df_sub, syarat):
            continue

        st.markdown(f'<div class="bagian"><small class="keterangan">{b["pertanyaan"]}</small></div>', unsafe_allow_html=True)

        if b["id"] == "distribusi_gol":
            total_gol = (df_sub["gol_kandang"] + df_sub["gol_tandang"]).clip(upper=7)
            dist = total_gol.value_counts(normalize=True).sort_index().reset_index()
            dist.columns = ["total_gol", "persen"]
            dist["persen"] = dist["persen"] * 100
            dist["gol_label"] = dist["total_gol"].apply(lambda g: f"{g}+" if g == 7 else str(g))

            chart = alt.Chart(dist).mark_bar(color=aksen, cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X("gol_label:O", title="Total gol dalam pertandingan", sort=None, axis=alt.Axis(grid=False)),
                y=alt.Y("persen:Q", title="Persentase pertandingan (%)", axis=alt.Axis(grid=True)),
                tooltip=["gol_label", alt.Tooltip("persen:Q", format=".1f")],
            ).properties(title=b["judul"], height=280).configure_title(
                font="IBM Plex Sans", fontSize=18, fontWeight=600, color="#0E1F18", anchor="start"
            ).configure_axis(
                domain=False, ticks=False, labelColor="#65736C", titleColor="#65736C",
                labelFont="IBM Plex Sans Condensed", titleFont="IBM Plex Sans",
                labelFontSize=13, titleFontSize=13
            ).configure_axisY(gridColor=GARIS, gridWidth=1)
            st.altair_chart(chart, use_container_width=True)

        elif b["id"] == "keuntungan_kandang":
            t = tren_per_musim(df_sub, "menang_kandang")
            t["nilai"] = t["nilai"] * 100
            t["seri"] = "Liga"
            chart = grafik_dasar(
                t, x="musim", y="nilai", judul=b["judul"], sorot="Liga",
                aksen=aksen, seri="seri", label_x="Musim kompetisi", label_y="Persentase menang kandang (%)"
            ).properties(height=280)
            st.altair_chart(chart, use_container_width=True)

        elif b["id"] == "tembakan_vs_gol":
            t_tembakan = df_sub.groupby("musim")[["tembakan_kandang", "gol_kandang"]].mean().reset_index()
            t_tembakan["seri"] = "Rata-rata Tembakan"
            t_tembakan["nilai"] = t_tembakan["tembakan_kandang"]
            chart = grafik_dasar(
                t_tembakan, x="musim", y="nilai", judul=b["judul"], sorot="Rata-rata Tembakan",
                aksen=aksen, seri="seri", label_x="Musim kompetisi", label_y="Tembakan per laga"
            ).properties(height=280)
            st.altair_chart(chart, use_container_width=True)

        elif b["id"] == "waktu_gol":
            t_b1 = tren_per_musim(df_sub, "gol_babak1")
            t_b2 = tren_per_musim(df_sub, "gol")
            t_b2["nilai"] = t_b2["nilai"] - t_b1["nilai"]
            t_b1["seri"] = "Babak Pertama"
            t_b2["seri"] = "Babak Kedua"
            t_waktu = pd.concat([t_b1, t_b2])
            chart = grafik_dasar(
                t_waktu, x="musim", y="nilai", judul=b["judul"], sorot="Babak Kedua",
                aksen=aksen, seri="seri", label_x="Musim kompetisi", label_y="Gol per laga"
            ).properties(height=280)
            st.altair_chart(chart, use_container_width=True)

        elif b["id"] == "disiplin":
            df_sub["kartu_kuning"] = df_sub["kartu_kuning_kandang"] + df_sub["kartu_kuning_tandang"]
            t_kartu = df_sub.groupby("musim")["kartu_kuning"].mean().reset_index()
            t_kartu["seri"] = "Kartu Kuning"
            t_kartu["nilai"] = t_kartu["kartu_kuning"]
            chart = grafik_dasar(
                t_kartu, x="musim", y="nilai", judul=b["judul"], sorot="Kartu Kuning",
                aksen=aksen, seri="seri", label_x="Musim kompetisi", label_y="Kartu kuning per laga"
            ).properties(height=280)
            st.altair_chart(chart, use_container_width=True)

        elif b["id"] == "konsistensi":
            pk_df = _poin_per_klub_per_musim(df_sub)
            chart = grafik_dasar(
                pk_df, x="musim", y="poin_per_laga", judul=b["judul"], sorot=klub,
                aksen=aksen, seri="klub", label_x="Musim kompetisi", label_y="Poin per pertandingan"
            ).properties(height=320)
            st.altair_chart(chart, use_container_width=True)

    if catatan_tidak_utuh:
        st.caption(
            "* Catatan data: Musim 2003/04 dan 2004/05 masing-masing tercatat 335 laga (45 laga hilang dari sumber data awal), "
            "dan musim berjalan 2026/27 baru memainkan 90 laga. Seluruh kalkulasi menggunakan ukuran per laga."
        )
