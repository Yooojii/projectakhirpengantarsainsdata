"""Halaman Prediksi & Simulasi: kalkulasi peluang hasil dan ruang eksperimen taktik."""
import copy
from html import escape
import os
from pathlib import Path
import pandas as pd
import streamlit as st

from gaya.komponen import bar_atribut, papan_skor, warna_aksen
from inti.agregasi import agregasi_fitur, kalibrasi
from inti.data import klub_musim, muat_pertandingan
from inti.fitur import fitur_tim
from inti.jadwal import jadwal_sisa
from inti.klub import warna_klub
from inti.model import distribusi_skor, pembanding, prediksi, skor_utama
from inti.pemain import bangkitkan_skuad
from inti.sesi import BULAN, JALUR_DATA, JALUR_METRIK, JALUR_MODEL

AKAR = Path(__file__).resolve().parent.parent
JALUR_PREDIKSI_UJI = AKAR / "model" / "prediksi_uji.csv"

ATRIBUT_UTAMA = {
    "DEP": "penyelesaian",
    "TEN": "kreativitas",
    "BEL": "antisipasi",
    "KIP": "refleks",
}


def siapkan_sesi(df: pd.DataFrame, klub_k: str, klub_t: str, tanggal: pd.Timestamp) -> dict:
    """Membangkitkan skuad dan parameter kalibrasi untuk sepasang klub (fungsi murni)."""
    sk = bangkitkan_skuad(df, klub_k, tanggal)
    st_ = bangkitkan_skuad(df, klub_t, tanggal)
    kk = kalibrasi(df, klub_k, tanggal)
    kt = kalibrasi(df, klub_t, tanggal)
    pk = float(fitur_tim(df, klub_k, tanggal, True)["poin_lima_laga"])
    pt = float(fitur_tim(df, klub_t, tanggal, False)["poin_lima_laga"])

    return {
        "skuad_kandang": sk,
        "skuad_tandang": st_,
        "skuad_kandang_awal": copy.deepcopy(sk),
        "skuad_tandang_awal": copy.deepcopy(st_),
        "konst_kandang": kk,
        "konst_tandang": kt,
        "poin_kandang": pk,
        "poin_tandang": pt,
    }


def hitung_prediksi(sesi: dict) -> dict:
    """Menghitung vektor fitur dari skuad saat ini dan memprediksi hasil pertandingan."""
    fk = agregasi_fitur(
        sesi["skuad_kandang"],
        sesi["konst_kandang"],
        sesi["poin_kandang"],
        kandang=True,
    )
    ft = agregasi_fitur(
        sesi["skuad_tandang"],
        sesi["konst_tandang"],
        sesi["poin_tandang"],
        kandang=False,
    )

    p = prediksi(fk, ft, model=sesi.get("model"))
    dist = distribusi_skor(p["gol_harapan_kandang"], p["gol_harapan_tandang"])

    # Hasil terkuat ditentukan dari argmax 3 probabilitas model
    p_map = {"H": p["p_menang_kandang"], "D": p["p_seri"], "A": p["p_menang_tandang"]}
    hasil_terkuat = max(p_map, key=p_map.get)
    skor = skor_utama(dist, hasil_terkuat)

    # 5 skor teratas beserta peluangnya
    lima_teratas = sorted(dist.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        **p,
        "skor": skor,
        "lima_teratas": lima_teratas,
    }


def selisih(awal: dict, sekarang: dict) -> dict:
    """Mengembalikan hanya pasangan kunci yang nilainya berubah signifikan antara dua keadaan."""
    hasil = {}
    for k in awal:
        if k not in sekarang:
            continue
        v_awal, v_sek = awal[k], sekarang[k]
        if isinstance(v_awal, float) and isinstance(v_sek, float):
            if abs(v_awal - v_sek) > 1e-5:
                hasil[k] = v_sek
        elif v_awal != v_sek:
            hasil[k] = v_sek
    return hasil


def tampil() -> None:
    df = muat_pertandingan(str(JALUR_DATA))
    klub_saya = st.session_state.get("klub", "Arsenal")
    aksen = warna_aksen(warna_klub(klub_saya))

    st.markdown('<div class="bagian"><h3>Prediksi & Lab Simulasi Pertandingan</h3></div>', unsafe_allow_html=True)

    # 1. Pemilih Laga
    tipe_laga = st.radio(
        "Pilih Sumber Pertandingan",
        ["Jadwal Simulasi Musim", "Pasangan Bebas"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if tipe_laga == "Jadwal Simulasi Musim":
        sisa = jadwal_sisa(df)
        laga_klub = sisa[(sisa["tim_kandang"] == klub_saya) | (sisa["tim_tandang"] == klub_saya)]
        if laga_klub.empty:
            laga_klub = sisa.head(10)

        daftar_opsi = [
            f"{r.tim_kandang} vs {r.tim_tandang} ({r.tanggal.day} {BULAN[r.tanggal.month - 1]} {r.tanggal.year})"
            for r in laga_klub.itertuples()
        ]
        pilihan_idx = st.selectbox("Pilih Jadwal Pertandingan", range(len(daftar_opsi)), format_func=lambda i: daftar_opsi[i])
        laga_terpilih = laga_klub.iloc[pilihan_idx]
        tim_k = laga_terpilih["tim_kandang"]
        tim_t = laga_terpilih["tim_tandang"]
        tgl_laga = pd.Timestamp(laga_terpilih["tanggal"])
    else:
        semua_20 = klub_musim(df, "2026/27")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            tim_k = st.selectbox("Tuan Rumah (Kandang)", semua_20, index=semua_20.index(klub_saya))
        with col_p2:
            lawan_opsi = [k for k in semua_20 if k != tim_k]
            tim_t = st.selectbox("Tim Tamu (Tandang)", lawan_opsi)
        tgl_laga = pd.Timestamp("2026-11-07")

    kunci_sesi = f"sim_{tim_k}_{tim_t}_{tgl_laga.strftime('%Y%m%d')}"
    if st.session_state.get("kunci_sesi_aktif") != kunci_sesi:
        st.session_state["kunci_sesi_aktif"] = kunci_sesi
        st.session_state["sesi_simulasi"] = siapkan_sesi(df, tim_k, tim_t, tgl_laga)

    sesi = st.session_state["sesi_simulasi"]
    sesi["model"] = st.session_state.get("model")

    # Hitung keadaan awal dan keadaan saat ini
    sesi_awal = {
        "skuad_kandang": sesi["skuad_kandang_awal"],
        "skuad_tandang": sesi["skuad_tandang_awal"],
        "konst_kandang": sesi["konst_kandang"],
        "konst_tandang": sesi["konst_tandang"],
        "poin_kandang": sesi["poin_kandang"],
        "poin_tandang": sesi["poin_tandang"],
        "model": sesi.get("model"),
    }
    pred_awal = hitung_prediksi(sesi_awal)
    pred_sekarang = hitung_prediksi(sesi)
    perubahan = selisih(pred_awal, pred_sekarang)
    ada_perubahan = bool(perubahan)

    # 2. Papan Prediksi
    peluang_now = {
        "menang": pred_sekarang["p_menang_kandang"],
        "seri": pred_sekarang["p_seri"],
        "kalah": pred_sekarang["p_menang_tandang"],
    }
    st.markdown(
        papan_skor(tim_k, tim_t, pred_sekarang["skor"], peluang_now, aksen=aksen, berubah=ada_perubahan),
        unsafe_allow_html=True,
    )

    # 3. Lima Skor Teratas
    baris_skor = []
    for (sk, st_), p_skor in pred_sekarang["lima_teratas"]:
        baris_skor.append(
            f'<span style="display: inline-block; padding: 4px 10px; background: var(--permukaan); '
            f'border: 1px solid var(--garis); border-radius: 4px; margin-right: 8px; font-size: 13px;">'
            f'<strong style="font-family: var(--huruf-sempit);">{sk} - {st_}</strong> '
            f'<span style="color: var(--teks-2); font-size: 12px;">({p_skor * 100:.1f}%)</span>'
            f'</span>'
        )
    st.markdown(
        f'<div style="margin-top: 8px; margin-bottom: 24px;">'
        f'<small class="keterangan" style="display: block; margin-bottom: 6px;">Kemungkinan Skor Terbesar:</small>'
        f'<div>{"".join(baris_skor)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # 4. Blok Umpan Balik Perubahan (Selisih)
    if ada_perubahan:
        st.markdown(
            '<div class="panel" style="border-left: 4px solid var(--aksen); margin-bottom: 24px;">'
            '<div style="font-weight: 600; font-size: 14px; margin-bottom: 8px;">Dibanding Susunan Asli</div>'
            '<div style="display: flex; gap: 32px; flex-wrap: wrap;">'
            f'<div><span class="keterangan">Peluang Menang Tuan Rumah:</span> '
            f'<strong>{pred_awal["p_menang_kandang"] * 100:.1f}% → {pred_sekarang["p_menang_kandang"] * 100:.1f}%</strong></div>'
            f'<div><span class="keterangan">Gol Diharapkan ({tim_k}):</span> '
            f'<strong>{pred_awal["gol_harapan_kandang"]:.2f} → {pred_sekarang["gol_harapan_kandang"]:.2f}</strong></div>'
            f'<div><span class="keterangan">Gol Diharapkan ({tim_t}):</span> '
            f'<strong>{pred_awal["gol_harapan_tandang"]:.2f} → {pred_sekarang["gol_harapan_tandang"]:.2f}</strong></div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("Kembalikan ke susunan asli"):
            sesi["skuad_kandang"] = copy.deepcopy(sesi["skuad_kandang_awal"])
            sesi["skuad_tandang"] = copy.deepcopy(sesi["skuad_tandang_awal"])
            st.rerun()

    # 5. Susunan Pemain & Penggeser Atribut
    st.markdown('<div class="bagian"><h3>Susunan Pemain & Atribut</h3></div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="font-size: 14px; color: var(--teks-2);">'
        'Geser atribut utama pemain untuk mensimulasikan kenaikan atau penurunan performa di lapangan. '
        'Bentuk permainan diambil dari hasil nyata dan tidak bisa diubah.'
        '</p>',
        unsafe_allow_html=True,
    )

    is_kandang_saya = tim_k == klub_saya
    skuad_terbuka = sesi["skuad_kandang"] if is_kandang_saya else sesi["skuad_tandang"]
    nama_terbuka = tim_k if is_kandang_saya else tim_t

    skuad_terlipat = sesi["skuad_tandang"] if is_kandang_saya else sesi["skuad_kandang"]
    nama_terlipat = tim_t if is_kandang_saya else tim_k

    def _render_editor_skuad(skuad, prefix, is_saya):
        aksen_skuad = aksen if is_saya else None
        for idx, p in enumerate(skuad):
            if not p.inti:
                continue
            pos = p.posisi
            attr_utama = ATRIBUT_UTAMA.get(pos, "penyelesaian")
            nilai_skrg = p.atribut[attr_utama]

            c_info, c_slider = st.columns([1, 2])
            with c_info:
                st.markdown(
                    f'<div style="padding-top: 6px;">'
                    f'<span style="font-family: var(--huruf-sempit); font-weight: 600; width: 32px; display: inline-block;">{pos}</span> '
                    f'<span>{escape(p.nama)}</span> '
                    f'<span class="keterangan" style="font-size: 12px;">({attr_utama})</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with c_slider:
                baru = st.slider(
                    f"{p.nama}_{attr_utama}",
                    min_value=1,
                    max_value=99,
                    value=nilai_skrg,
                    key=f"{prefix}_{idx}_{attr_utama}",
                    label_visibility="collapsed",
                )
                if baru != nilai_skrg:
                    p.atribut[attr_utama] = baru

    # Skuad klub saya (Terbuka)
    st.markdown(f'<div class="dalam"><small class="keterangan">Susunan {escape(nama_terbuka)} (Klub Saya — Terbuka)</small></div>', unsafe_allow_html=True)
    _render_editor_skuad(skuad_terbuka, f"skuad_{nama_terbuka}", True)

    # Skuad lawan (Terlipat)
    with st.expander(f"Susunan Pemain Lawan: {nama_terlipat} (Terlipat)", expanded=False):
        _render_editor_skuad(skuad_terlipat, f"skuad_{nama_terlipat}", False)

    # 6. Evaluasi Model
    st.markdown('<div class="bagian"><h3>Evaluasi Model & Komparasi Pasar</h3></div>', unsafe_allow_html=True)
    ada_metrik = os.path.exists(str(JALUR_METRIK))
    ada_uji = os.path.exists(str(JALUR_PREDIKSI_UJI))

    if ada_metrik and ada_uji:
        try:
            df_uji = pd.read_csv(str(JALUR_PREDIKSI_UJI))
            hasil_pembanding = pembanding(df_uji)
            c_m1, c_m2, c_m3 = st.columns(3)
            with c_m1:
                st.markdown(
                    f'<div class="panel"><div class="keterangan">Akurasi Model</div>'
                    f'<div class="angka" style="font-size: 24px; font-weight: 600; color: {aksen};">'
                    f'{hasil_pembanding["model"] * 100:.1f}%</div></div>',
                    unsafe_allow_html=True,
                )
            with c_m2:
                st.markdown(
                    f'<div class="panel"><div class="keterangan">Acuan Selalu Kandang</div>'
                    f'<div class="angka" style="font-size: 24px; font-weight: 600;">'
                    f'{hasil_pembanding["selalu_kandang"] * 100:.1f}%</div></div>',
                    unsafe_allow_html=True,
                )
            with c_m3:
                st.markdown(
                    f'<div class="panel"><div class="keterangan">Tebakan Odds Bandar</div>'
                    f'<div class="angka" style="font-size: 24px; font-weight: 600;">'
                    f'{hasil_pembanding["ikut_odds"] * 100:.1f}%</div></div>',
                    unsafe_allow_html=True,
                )
        except Exception:
            st.markdown('<p class="keterangan">Evaluasi menunggu model dari proses pemodelan.</p>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="panel"><p class="keterangan" style="margin: 0;">'
            'Evaluasi menunggu model dari proses pemodelan.'
            '</p></div>',
            unsafe_allow_html=True,
        )

    # 7. Key Insights (Apa yang kami temukan)
    st.markdown('<div class="bagian"><h3>Apa yang kami temukan</h3></div>', unsafe_allow_html=True)
    st.markdown(
        "- **Efektivitas Konversi Peluang**: Peningkatan pada atribut penyelesaian penyerang memberikan "
        "dampak matematis yang lebih konsisten terhadap peluang kemenangan dibanding sekadar memperbanyak tembakan melenceng.\n"
        "- **Stabilitas Faktor Kandang**: Keunggulan bermain di kandang menyumbang bobot peluang yang signifikan "
        "bahkan ketika menghadapi lawan yang memiliki peringkat performa liga lebih tinggi.\n"
        "- **Pengaruh Lini Pertahanan**: Pertahanan yang kokoh (antisipasi dan disiplin posisi) mampu meredam "
        "agresivitas tim lawan dan secara langsung memangkas rasio kebobolan harapan."
    )

    # 8. Rekomendasi untuk Pelatih
    st.markdown('<div class="bagian"><h3>Rekomendasi untuk pelatih</h3></div>', unsafe_allow_html=True)
    st.markdown(
        "1. **Fokuskan Latihan pada Kualitas Penyelesaian Akhir**: Hindari instruksi spekulatif dari luar kotak penalti; "
        "peluang bersih di dalam kotak penalti meningkatkan ekspektasi gol secara terukur.\n"
        "2. **Manajemen Disiplin Area Kritis**: Pelanggaran di sepertiga akhir pertahanan kerap berujung pada peluang bola mati "
        "berbahaya yang membalikkan momentum pertandingan kandang.\n"
        "3. **Rotasi Skuad Sesuai Karakter Lawan**: Saat menghadapi lawan dengan kreativitas tinggi, tingkatkan peran gelandang bertahan "
        "dengan atribut rebutan dan antisipasi tinggi guna memutus aliran bola sebelum masuk kotak penalti."
    )

    # 9. Kaki Halaman (Catatan Permanen Simulasi)
    st.markdown(
        '<div style="margin-top: 48px; padding-top: 16px; border-top: 1px solid var(--garis);">'
        '<small class="keterangan" style="font-size: 13px; color: var(--teks-2);">'
        'Atribut pemain adalah data simulasi yang dikalibrasi dari statistik tim, bukan penilaian pemain sungguhan.'
        '</small>'
        '</div>',
        unsafe_allow_html=True,
    )
