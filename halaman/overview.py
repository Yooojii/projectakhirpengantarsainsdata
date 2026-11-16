"""Halaman Overview: ringkasan proyek, data, kelengkapan, dan dokumentasi metodologi."""
import pandas as pd
import streamlit as st

from gaya.komponen import papan_skor, warna_aksen
from inti.data import KELOMPOK_KOLOM, muat_pertandingan
from inti.fitur import fitur_tim
from inti.jadwal import jadwal_sisa
from inti.klub import warna_klub
from inti.model import distribusi_skor, prediksi, skor_utama
from inti.sesi import BULAN, JALUR_DATA


def tabel_kelengkapan(df: pd.DataFrame) -> pd.DataFrame:
    """Tabel kelengkapan kolom per kelompok beserta status dan alasannya untuk model."""
    alasan_dict = {
        "identitas": (
            "Hanya penanda identitas laga, jadwal, wasit, dan pemisah temporal; "
            "bukan fitur masukan model."
        ),
        "hasil": (
            "Target label klasifikasi (menang/seri/kalah) dan skor aktual; "
            "bukan variabel prediktor."
        ),
        "statistik_dasar": (
            "Fitur utama agregasi 10 laga terakhir, terisi 100% pada seluruh "
            "9.880 pertandingan tanpa data bolong."
        ),
        "odds": (
            "Hanya tersedia untuk laga lampau (sejak 2019/20); dilarang sebagai fitur "
            "agar model dapat memprediksi laga mendatang."
        ),
        "statistik_lanjutan": (
            "Cakupan sangat tipis (1% untuk statistik API, xG hanya pada 2026/27); "
            "dilarang sebagai fitur agar model tidak belajar dari data bolong."
        ),
    }

    baris = []
    for kelompok, kolom_list in KELOMPOK_KOLOM.items():
        sub = df[kolom_list]
        cakupan = round(100.0 * float(sub.notna().to_numpy().mean()), 1)
        dipakai = kelompok == "statistik_dasar"
        baris.append({
            "kelompok": kelompok,
            "cakupan": cakupan,
            "dipakai_model": dipakai,
            "alasan": alasan_dict[kelompok],
        })
    df_res = pd.DataFrame(baris)
    df_res["dipakai_model"] = df_res["dipakai_model"].astype(object)
    return df_res


def _format_tanggal(ts: pd.Timestamp) -> str:
    hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][ts.dayofweek]
    return f"{hari}, {ts.day} {BULAN[ts.month - 1]} {ts.year}"


def tampil() -> None:
    df = muat_pertandingan(str(JALUR_DATA))
    klub = st.session_state.get("klub", "Arsenal")
    aksen = warna_aksen(warna_klub(klub))

    st.markdown(
        '<div style="font-size: 13px; color: var(--teks-2); margin-bottom: 4px;">'
        'PDS UAS — Dashboard Pelatih Liga Inggris</div>',
        unsafe_allow_html=True,
    )

    # Hero: laga berikutnya klub terpilih
    sisa = jadwal_sisa(df)
    laga_klub = sisa[(sisa["tim_kandang"] == klub) | (sisa["tim_tandang"] == klub)]
    if not laga_klub.empty:
        laga = laga_klub.iloc[0]
        tgl = pd.Timestamp(laga["tanggal"])
        tk, tt = laga["tim_kandang"], laga["tim_tandang"]
        fk = fitur_tim(df, tk, tgl, kandang=True)
        ft = fitur_tim(df, tt, tgl, kandang=False)
        pred = prediksi(fk, ft, model=st.session_state.get("model"))
        dist = distribusi_skor(pred["gol_harapan_kandang"], pred["gol_harapan_tandang"])
        p_map = {"H": pred["p_menang_kandang"], "D": pred["p_seri"], "A": pred["p_menang_tandang"]}
        hasil_terkuat = max(p_map, key=p_map.get)
        skor = skor_utama(dist, hasil_terkuat)
        peluang = {
            "menang": pred["p_menang_kandang"],
            "seri": pred["p_seri"],
            "kalah": pred["p_menang_tandang"],
        }

        st.markdown(
            f'<div style="font-family: var(--huruf-sempit); font-size: 15px; color: var(--teks-2); '
            f'margin-top: 12px; margin-bottom: 4px;">{_format_tanggal(tgl)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            papan_skor(tk, tt, skor, peluang, aksen=aksen, berubah=False),
            unsafe_allow_html=True,
        )

    # Latar Belakang & Tujuan
    st.markdown(
        '<div style="margin-top: 32px;">'
        '<p style="max-width: 68ch; font-size: 16px; line-height: 1.6; margin-bottom: 12px;">'
        'Sembilan ribu delapan ratus delapan puluh pertandingan sejak tahun 2000. '
        'Dashboard ini memerasnya jadi satu hal: apa yang masuk akal dilakukan hari Sabtu.'
        '</p>'
        '<p style="max-width: 68ch; font-size: 16px; line-height: 1.6;">'
        'Dibangun khusus untuk membantu pelatih menganalisis kekuatan lawan akhir pekan, '
        'mengidentifikasi pola kompetisi yang berulang, dan mensimulasikan dampak perubahan '
        'susunan pemain berbasis data empiris nyata.'
        '</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Pertanyaan yang bisa dijawab
    st.markdown('<div class="bagian"><h3>Yang bisa dijawab di sini</h3></div>', unsafe_allow_html=True)
    st.markdown(
        "- **Seberapa berat lawan berikutnya** — probabilitas kemenangan, peluang seri, dan skor paling realistis.\n"
        "- **Pola apa yang berulang di liga** — tren gol, keunggulan kandang, dan korelasi disiplin terhadap hasil.\n"
        "- **Apa yang berubah kalau form pemain naik** — simulasi geseran atribut pemain terhadap hasil akhir."
    )

    # Angka ringkas data
    st.markdown('<div class="bagian"><h3>Data Pertandingan</h3></div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            '<div class="panel"><div class="keterangan">Total Laga</div>'
            '<div class="angka" style="font-size: 28px; font-weight: 600;">9.880</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            '<div class="panel"><div class="keterangan">Rentang Waktu</div>'
            '<div class="angka" style="font-size: 28px; font-weight: 600;">27 Musim</div></div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            '<div class="panel"><div class="keterangan">Jumlah Klub</div>'
            '<div class="angka" style="font-size: 28px; font-weight: 600;">46 Klub</div></div>',
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            '<div class="panel"><div class="keterangan">Jumlah Variabel</div>'
            '<div class="angka" style="font-size: 28px; font-weight: 600;">56 Kolom</div></div>',
            unsafe_allow_html=True,
        )

    # Tabel kelengkapan kolom
    st.markdown('<div class="dalam">', unsafe_allow_html=True)
    tabel_df = tabel_kelengkapan(df)
    baris_html = []
    for row in tabel_df.itertuples():
        status = "Ya" if row.dipakai_model else "Tidak"
        warna_status = "var(--aksen)" if row.dipakai_model else "var(--teks-2)"
        baris_html.append(
            f'<tr><td class="teks">{row.kelompok}</td>'
            f'<td>{row.cakupan}%</td>'
            f'<td style="color: {warna_status}; font-weight: 600;">{status}</td>'
            f'<td class="teks" style="font-size: 13px; color: var(--teks-2);">{row.alasan}</td></tr>'
        )
    tabel_html = (
        '<table class="tabel" style="width: 100%; margin-top: 16px;">'
        '<thead><tr>'
        '<th class="teks">Kelompok Kolom</th>'
        '<th>Cakupan</th>'
        '<th>Dipakai Model</th>'
        '<th class="teks">Alasan & Pertimbangan</th>'
        '</tr></thead>'
        f'<tbody>{"".join(baris_html)}</tbody>'
        '</table>'
    )
    st.markdown(tabel_html, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Expander 1: Pra-pemrosesan Data
    with st.expander("Bagaimana data dibersihkan", expanded=False):
        st.markdown(
            "1. **Jendela Rolling 10 Pertandingan Melintasi Batas Musim**\n"
            "   Fitur tim dihitung dari performa 10 laga terakhir (kandang dan tandang digabung) "
            "   sebelum tanggal pertandingan. Untuk klub promosi seperti Coventry City, 10 laga terakhirnya "
            "   menjangkau riwayat hingga Mei 2001.\n\n"
            "2. **Penanganan Musim yang Tidak Utuh**\n"
            "   Musim 2003/04 dan 2004/05 masing-masing hanya memuat 335 laga (45 laga hilang dari sumber). "
            "   Seluruh tren kompetisi dianalisis menggunakan rata-rata per laga, bukan total musiman.\n\n"
            "3. **Pembersihan Kolom Pekan**\n"
            "   Kolom `pekan` hanya terisi 102 laga pada musim 2024/25 sehingga tidak digunakan; "
            "   seluruh referensi waktu menggunakan tanggal aktual pertandingan.\n\n"
            "4. **Pengecualian Odds dan Statistik Lanjutan dari Fitur Model**\n"
            "   Odds dilarang sebagai fitur karena tidak tersedia untuk laga mendatang. "
            "   Statistik lanjutan (possession, umpan akurat, xG API) hanya terisi ~1% sehingga "
            "   tidak valid untuk melatih model 27 musim.\n\n"
            "5. **Koreksi Data Anomali Tembakan (Poin F4)**\n"
            "   Tiga baris data memiliki tembakan tepat melebihi total tembakan "
            "   (Coventry 14 Okt 2000, Bradford 13 Apr 2001, dan West Ham 15 Agu 2021). "
            "   Tembakan tepat diklem setara total tembakan agar rasio akurasi tidak melampaui 1,0."
        )

    # Expander 2: Metodologi Pemodelan & Evaluasi
    with st.expander("Model yang dipakai dan cara mengujinya", expanded=False):
        st.markdown(
            "1. **Klasifikasi Multi-Kelas Hasil Laga**\n"
            "   Model memprediksi probabilitas `H` (kandang menang), `D` (seri), dan `A` (tandang menang) "
            "   menggunakan 10 fitur dasar per tim (total 20 fitur berpasangan).\n\n"
            "2. **Jalan Mundur Poisson**\n"
            "   Jika berkas model terlatih (`model/model.joblib`) belum tersedia, sistem secara otomatis "
            "   menggunakan distribusi Poisson berbasis rata-rata gol dicetak dan kebobolan tim.\n\n"
            "3. **Evaluasi Temporal Bebas Kebocoran**\n"
            "   Data uji dipisahkan secara temporal (musim 2019/20 ke atas) dan dievaluasi terhadap dua pembanding: "
            "   strategi acuan 'selalu kandang' dan akurasi tebakan pasar (odds terendah)."
        )
