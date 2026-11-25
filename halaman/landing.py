"""Landing page BallBoard: pengantar dashboard sebelum pengguna masuk.

Isinya ringkasan dashboard, asal data, langkah pra-pemrosesan, cara kerja model, dan
temuan utama. Semua angka dihitung dari data dan berkas metrik model, bukan ditulis
tangan, supaya tetap benar ketika data diperbarui.

Tombol masuk berupa tautan `?buka=overview|analisis|history`; `app.py` membacanya,
menandai sesi sudah masuk, lalu membuka tab yang diminta.
"""
import base64
import json
from functools import lru_cache
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from gaya.komponen import _uri_logo
from inti.data import muat_pertandingan
from inti.liga import juara, kandang_tandang, tren_musim
from inti.sesi import AKAR, BULAN, JALUR_DATA

_CSS = Path(__file__).resolve().parent.parent / "gaya" / "landing.css"
JALUR_PERBANDINGAN = AKAR / "pipeline" / "model" / "perbandingan_model.json"
JALUR_METRIK_MODEL = AKAR / "model" / "metrik.json"


def _koma(v: float, desimal: int = 1) -> str:
    return f"{v:.{desimal}f}".replace(".", ",")


def _ribuan(n: int) -> str:
    return f"{n:,}".replace(",", ".")


@st.cache_data(show_spinner=False)
def fakta(df: pd.DataFrame) -> dict:
    """Angka-angka yang ditampilkan di landing page, semuanya dari data."""
    gol = df["gol_kandang"] + df["gol_tandang"]
    hasil = df["hasil"].value_counts(normalize=True)
    tren = tren_musim(df).set_index("musim")
    musim_penuh = [m for m in tren.index if tren.loc[m, "laga"] >= 380]
    awal, akhir = musim_penuh[0], musim_penuh[-1]
    babak1 = df.dropna(subset=["gol_kandang_babak1", "gol_tandang_babak1"])
    gol_b1 = babak1["gol_kandang_babak1"] + babak1["gol_tandang_babak1"]
    gol_ft = babak1["gol_kandang"] + babak1["gol_tandang"]
    unggul = babak1[babak1["gol_kandang_babak1"] != babak1["gol_tandang_babak1"]]
    tetap_menang = (
        ((unggul["gol_kandang_babak1"] > unggul["gol_tandang_babak1"]) & (unggul["hasil"] == "H"))
        | ((unggul["gol_kandang_babak1"] < unggul["gol_tandang_babak1"]) & (unggul["hasil"] == "A"))
    )
    total_gol = gol.clip(upper=6).value_counts(normalize=True)
    poin = next(b for b in kandang_tandang(df) if b["label"] == "Poin per laga")
    gelar = juara(df)
    terakhir = df["tanggal"].max()
    lengkap = df.notna().mean()
    return {
        "laga": len(df),
        "musim": df["musim"].nunique(),
        "musim_awal": str(df["musim"].min()),
        "musim_akhir": str(df["musim"].max()),
        "tanggal_akhir": f"{terakhir.day} {BULAN[terakhir.month - 1]} {terakhir.year}",
        "klub": len(set(df["tim_kandang"]) | set(df["tim_tandang"])),
        "kolom": df.shape[1],
        "kolom_penuh": int((lengkap == 1).sum()),
        "kolom_tipis": int((lengkap < 0.5).sum()),
        "gol": int(gol.sum()),
        "gol_per_laga": float(gol.mean()),
        "menang_kandang": 100 * float(hasil.get("H", 0)),
        "seri": 100 * float(hasil.get("D", 0)),
        "menang_tandang": 100 * float(hasil.get("A", 0)),
        "poin_kandang": poin["kandang"],
        "poin_tandang": poin["tandang"],
        "skor_umum": int(total_gol.idxmax()),
        "skor_umum_persen": 100 * float(total_gol.max()),
        "gol_babak2": 100 * float((gol_ft - gol_b1).sum() / gol_ft.sum()),
        "unggul_jeda_menang": 100 * float(tetap_menang.mean()),
        "konversi": 100 * float(gol.sum() / (df["tembakan_kandang"] + df["tembakan_tandang"]).sum()),
        "langgar_awal": float(tren.loc[awal, "pelanggaran"]),
        "langgar_akhir": float(tren.loc[akhir, "pelanggaran"]),
        "musim_penuh_awal": awal,
        "musim_penuh_akhir": akhir,
        "juara": gelar.iloc[0]["klub"],
        "gelar": int(gelar.iloc[0]["gelar"]),
        "musim_selesai": int(gelar["gelar"].sum()),
        "odds_sejak": str(df.loc[df["odds_kandang"].notna(), "musim"].min()),
        "lanjutan_sejak": str(df.loc[df["penguasaan_bola_kandang"].notna(), "musim"].min()),
    }


def _model() -> tuple[dict, dict]:
    perbandingan = json.loads(JALUR_PERBANDINGAN.read_text(encoding="utf-8")) \
        if JALUR_PERBANDINGAN.is_file() else {}
    metrik = json.loads(JALUR_METRIK_MODEL.read_text(encoding="utf-8")) \
        if JALUR_METRIK_MODEL.is_file() else {}
    return perbandingan, metrik


@lru_cache(maxsize=None)
def _uri_foto(nama: str) -> str:
    """Foto kartu tab (WebP 720 px, dipotong dari foto pilihan kelompok) sebagai data URI."""
    jalur = AKAR / "data" / "landing" / f"{nama}.webp"
    if not jalur.is_file():
        return ""
    return "data:image/webp;base64," + base64.b64encode(jalur.read_bytes()).decode("ascii")


_SUDAH_DIPANASKAN = False


def _panaskan_modul(df: pd.DataFrame) -> None:
    """Siapkan Altair, SciPy, dan logo klub versi kecil di utas latar selagi pengguna membaca
    landing page, supaya membuka dashboard pertama kali tidak menunggu sekitar 4 detik.

    Utas ini sengaja hanya mengimpor library pihak ketiga. Modul proyek (halaman/, inti/,
    gaya/) dimuat ulang Streamlit setiap kali berkasnya berubah; mengimpornya dari utas lain
    bisa bertabrakan dengan proses itu dan menimbulkan KeyError. Semua yang dibutuhkan dari
    proyek (daftar logo, fungsi pengecil) disiapkan di utas utama lalu diteruskan."""
    global _SUDAH_DIPANASKAN
    if _SUDAH_DIPANASKAN:
        return
    _SUDAH_DIPANASKAN = True
    import threading

    from gaya.komponen import LOGO_KECIL, LOGO_SEDANG
    from inti.klub import logo_klub

    klub = set(df["tim_kandang"]) | set(df["tim_tandang"])
    logo = [str(j) for j in map(logo_klub, klub) if j is not None]
    perkecil = _uri_logo

    def _siapkan() -> None:
        import time
        time.sleep(2)  # beri jalan dulu ke landing page yang sedang digambar
        try:
            import altair  # noqa: F401
            import scipy.stats  # noqa: F401
            for jalur in logo:  # hasilnya tersimpan di lru_cache _uri_logo
                perkecil(jalur, LOGO_KECIL)
                perkecil(jalur, LOGO_SEDANG)
        except Exception:  # pemanasan saja; kalau gagal, semuanya tetap dimuat biasa nanti
            pass

    threading.Thread(target=_siapkan, name="panaskan-dashboard", daemon=True).start()


# --------------------------------------------------------------- potongan HTML

TOMBOL_MASUK = '<a class="lp-tombol lp-utama" href="?buka=overview" target="_self">Buka Dashboard</a>'


def _nav(logo: str) -> str:
    tautan = [("#overview", "Overview"), ("#dataset", "Dataset"), ("#praproses", "Pre-Processing"),
              ("#modelling", "Modelling"), ("#insight", "Insight")]
    isi = "".join(f'<a href="{h}">{t}</a>' for h, t in tautan)
    return (
        '<nav class="lp-nav" aria-label="Navigasi landing page">'
        f'<a class="lp-merek" href="#atas"><img src="{logo}" alt="">BallBoard</a>'
        f'<div class="lp-tautan">{isi}<span class="lp-penanda" aria-hidden="true"></span></div>'
        f'{TOMBOL_MASUK}</nav>'
    )


def _hero(f: dict, lambang: str) -> str:
    return f'''
<section class="lp-hero" id="atas">
  <div class="lp-lapangan" aria-hidden="true"><i></i><i></i><i></i></div>
  <div class="lp-hero-isi">
    <span class="lp-chip lp-masuk" style="--d:0">{f["musim"]} musim Premier League, {_ribuan(f["laga"])} laga</span>
    <h1 class="lp-masuk" style="--d:1">{f["musim"]} musim,<span class="lp-redam">satu papan.</span></h1>
    <p class="lp-masuk" style="--d:2">BallBoard merangkum statistik setiap laga Liga Inggris sejak
      {escape(f["musim_awal"])}, membandingkan klub dari musim ke musim, dan memperkirakan hasil
      pertandingan dengan model statistik.</p>
    <div class="lp-aksi lp-masuk" style="--d:3">
      <a class="lp-tombol lp-kaca" href="#overview">Lihat isinya</a>
    </div>
  </div>
  <div class="lp-hero-visual" aria-hidden="true">
    <img class="lp-lambang" src="{lambang}" alt="">
    <div class="lp-kartu-apung lp-apung-1">
      <small>Tuan rumah menang</small>
      <b>{_koma(f["menang_kandang"])}%</b>
      <span>dari {_ribuan(f["laga"])} laga</span>
    </div>
    <div class="lp-kartu-apung lp-apung-2">
      <small>Rata-rata gol</small>
      <b>{_koma(f["gol_per_laga"], 2)}</b>
      <span>per laga</span>
    </div>
    <div class="lp-kartu-apung lp-apung-3">
      <span class="lp-chip lp-chip-terang">Simulasi</span>
      <span>Perkiraan skor dan peluang menang tiap laga</span>
    </div>
  </div>
  <p class="lp-hero-kaki">Kelompok 8, tugas akhir Pengantar Sains Data</p>
</section>'''


def _overview() -> str:
    kartu = [
        ("Overview", "overview", "Gambaran seluruh liga atau satu klub: KPI, profil performa skala 1–5, "
         "tren per musim, kandang dibanding tandang, dan klub dengan gelar terbanyak.", "?buka=overview"),
        ("Match Analysis", "analisis", "Simulasikan dua klub untuk melihat perkiraan skor dan peluang "
         "menang, atau buka statistik lengkap laga yang sudah dimainkan.", "?buka=analisis"),
        ("History", "history", "Rekor pertemuan dua klub, bentuk sepuluh laga terakhir, dan klasemen "
         "musim berjalan dengan zona empat besar dan degradasi.", "?buka=history"),
    ]
    isi = "".join(
        f'<a class="lp-tab lp-muncul" href="{href}" target="_self">'
        f'<span class="lp-foto"><img src="{_uri_foto(foto)}" alt="" loading="lazy"></span>'
        f'<h3>{judul}</h3><p>{teks}</p><span class="lp-tab-kaki">Buka tab {judul}</span></a>'
        for judul, foto, teks, href in kartu
    )
    return f'''
<section class="lp-bagian" id="overview">
  <div class="lp-kepala lp-muncul">
    <h2>Explore Football Through Data.</h2>
    <p>Setiap statistik punya cerita. Analisis performa klub, simulasikan pertandingan, dan
      telusuri perjalanan kompetisi melalui data.</p>
  </div>
  <div class="lp-tiga">{isi}</div>
</section>'''


def _dataset(f: dict) -> str:
    angka = [
        (_ribuan(f["laga"]), "laga"),
        (str(f["musim"]), "musim"),
        (str(f["klub"]), "klub"),
        (str(f["kolom"]), "kolom"),
        (_ribuan(f["gol"]), "gol"),
    ]
    strip = "".join(f'<div class="lp-angka lp-muncul"><b>{a}</b><span>{t}</span></div>' for a, t in angka)
    centang = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>'
    utama = [
        "Musim, tanggal, tim kandang, dan tim tandang",
        "Skor akhir dan skor babak pertama, hasil (menang, seri, kalah)",
        "Tembakan dan tembakan tepat sasaran tiap tim",
        "Pelanggaran, sepak pojok, kartu kuning, dan kartu merah",
        "Wasit yang memimpin laga",
        "Jam kick-off dan rata-rata peluang bandar",
        "Statistik lanjutan: penguasaan bola, umpan, "
        "offside, tekel, penyelamatan kiper, dan xG",
    ]
    daftar_utama = "".join(f"<li>{centang}<span>{t}</span></li>" for t in utama)
    return f'''
<section class="lp-bagian" id="dataset">
  <div class="lp-kepala lp-muncul">
    <h2>Behind the Numbers</h2>
    <p>Mengenal sumber, periode, dan cakupan data yang menjadi dasar setiap insight.</p>
  </div>
  <div class="lp-strip">{strip}</div>
  <div class="lp-sumber lp-muncul">
    <div class="lp-sumber-kiri">
      <span class="lp-chip">Sumber utama</span>
      <h3>football-data.co.uk</h3>
      <dl class="lp-fakta">
        <div><dt>Periode</dt><dd>{escape(f["musim_awal"])} sampai {escape(f["musim_akhir"])}</dd></div>
        <div><dt>Laga terakhir</dt><dd>{f["tanggal_akhir"]}</dd></div>
        <div><dt>Bentuk</dt><dd>Satu berkas per musim, digabung menjadi satu tabel</dd></div>
      </dl>
    </div>
    <div class="lp-sumber-kanan">
      <h4>Isi tiap baris laga <small>{f["kolom"]} peubah</small></h4>
      <ul class="lp-centang">{daftar_utama}</ul>
    </div>
  </div>
</section>'''


def _praproses(f: dict) -> str:
    langkah = [
        ("Pengecekan struktur data",
         ["Berkas tiap musim dibaca, tanda BOM di nama kolom dibersihkan.",
          "Kode kolom diseragamkan, misalnya HS menjadi tembakan_kandang.",
          "Semua musim digabung lalu diurutkan menurut tanggal."],
         f"{f['kolom']} kolom, {_ribuan(f['laga'])} baris"),
        ("Kualitas data",
         [f"{f['kolom_penuh']} kolom inti terisi penuh: skor, tembakan, pelanggaran, pojok, kartu.",
          f"{f['kolom_tipis']} kolom terisi kurang dari separuh, tidak dipakai sebagai fitur.",
          "Tembakan tepat yang melebihi total tembakan (tiga baris) dibatasi."],
         "Tanpa nilai kosong di kolom inti"),
        ("Konversi tipe data",
         ["Tanggal dd/mm/yyyy menjadi datetime; baris tanpa tanggal atau tim dibuang.",
          "Statistik laga menjadi angka, hasil laga menjadi kategori H, D, A.",
          "Nama klub dari tiap sumber disamakan agar bisa digabung."],
         "Tanggal, angka, kategori"),
        ("Feature engineering",
         ["Bentuk tim dari sepuluh laga terakhir: tembakan, gol, poin, dan lainnya.",
          "Rata-rata bergerak tertimbang dan rating Elo tiap klub.",
          "Hanya laga sebelum tanggal pertandingan yang dipakai, tanpa kebocoran data."],
         "35 fitur per laga"),
    ]
    kartu = "".join(
        f'<li class="lp-langkah lp-muncul"><span class="lp-nomor">{i + 1}</span>'
        f'<h3>{judul}</h3><ul>{"".join(f"<li>{b}</li>" for b in butir)}</ul>'
        f'<span class="lp-langkah-kaki">{kaki}</span></li>'
        for i, (judul, butir, kaki) in enumerate(langkah)
    )
    return f'''
<section class="lp-bagian" id="praproses">
  <div class="lp-kepala lp-muncul">
    <h2>Data Pipeline</h2>
    <p>Empat langkah berurutan sebelum data siap dibaca dashboard dan dipakai melatih model.</p>
  </div>
  <ol class="lp-alur">{kartu}</ol>
</section>'''


def _modelling(perbandingan: dict, metrik: dict) -> str:
    urutan = ["Regresi Poisson", "Regresi logistik", "Random Forest", "LightGBM",
              "Peluang bandar (pembanding)"]
    baris = []
    for nama in urutan:
        m = perbandingan.get(nama)
        if not m:
            continue
        bandar = "bandar" in nama
        akurasi = 100 * m["akurasi_hasil"]
        baris.append(
            f'<div class="lp-model{" lp-bandar" if bandar else ""}">'
            f'<span class="lp-model-nama">{escape(nama.replace(" (pembanding)", ""))}</span>'
            f'<span class="lp-model-lajur"><i style="width:{akurasi / 60 * 100:.1f}%"></i></span>'
            f'<b>{_koma(akurasi)}%</b><small>log loss {_koma(m["log_loss"], 3)}</small></div>'
        )
    uji = metrik.get("uji", {})
    laga_uji = uji.get("laga", 480)
    musim_uji = " dan ".join(metrik.get("musim_uji", ["2025/26", "2026/27"]))
    akurasi_akhir = 100 * uji.get("akurasi_hasil", 0)
    akurasi_bandar = 100 * uji.get("akurasi_bandar", 0)
    rho = metrik.get("rho", -0.035)
    simulasi = _ribuan(int(metrik.get("simulasi", 20000)))
    poin = [
        ("Satu regresi per statistik",
         "Gol, tembakan, tembakan tepat, sepak pojok, pelanggaran, dan kartu, untuk kedua tim."),
        ("Koreksi Dixon-Coles",
         f"Peluang skor rendah seperti 0-0 dan 1-1 disesuaikan (ρ = {_koma(rho, 3)})."),
        ("Latih maju bertahap",
         "Perkiraan untuk satu musim hanya belajar dari musim-musim sebelumnya."),
        ("Simulasi sisa musim",
         f"{simulasi} simulasi untuk peluang juara, empat besar, dan degradasi."),
    ]
    poin_html = "".join(f'<div class="lp-poin lp-muncul"><b>{j}</b><p>{t}</p></div>' for j, t in poin)
    return f'''
<section class="lp-gelap" id="modelling">
  <div class="lp-gelap-kiri lp-muncul">
    <span class="lp-chip lp-chip-terang">Modelling</span>
    <h2>Memperkirakan skor, bukan sekadar menang atau kalah.</h2>
    <p>Model utama adalah regresi Poisson yang menduga jumlah gol tiap tim, lalu mengubahnya
      menjadi matriks peluang skor. Dari situ keluar peluang menang, seri, dan kalah. Dashboard
      memakai gabungan Poisson dan LightGBM dengan akurasi {_koma(akurasi_akhir)}%.</p>
    <p class="lp-catatan">Sepak bola memang sulit ditebak: rata-rata peluang bandar pun hanya
      tepat {_koma(akurasi_bandar)}% pada laga yang sama.</p>
  </div>
  <div class="lp-gelap-kanan lp-muncul">
    <div class="lp-model-kepala"><span>Akurasi hasil laga</span>
      <small>{laga_uji} laga uji, musim {escape(musim_uji)}</small></div>
    {"".join(baris)}
  </div>
  <div class="lp-poin-grid">{poin_html}</div>
</section>'''


def _insight(f: dict) -> str:
    kandang, seri, tandang = f["menang_kandang"], f["seri"], f["menang_tandang"]
    utama = f'''
  <div class="lp-sorotan lp-muncul">
    <div class="lp-sorotan-teks">
      <b>{_koma(kandang)}%</b>
      <h3>Kandang masih berpengaruh</h3>
      <p>Tuan rumah memenangi {_koma(kandang)}% laga, tamu hanya {_koma(tandang)}%. Rata-rata poin
        per laga {_koma(f["poin_kandang"], 2)} di kandang dan {_koma(f["poin_tandang"], 2)} di tandang.</p>
    </div>
    <div class="lp-hasil" role="img" aria-label="Kandang menang {_koma(kandang)} persen, seri {_koma(seri)} persen, tandang menang {_koma(tandang)} persen">
      <div class="lp-hasil-bar"><i style="flex:{kandang:.1f}"></i><i style="flex:{seri:.1f}"></i><i style="flex:{tandang:.1f}"></i></div>
      <div class="lp-hasil-label">
        <span style="flex:{kandang:.1f}"><i></i>Kandang menang<b>{_koma(kandang)}%</b></span>
        <span style="flex:{seri:.1f}"><i></i>Seri<b>{_koma(seri)}%</b></span>
        <span style="flex:{tandang:.1f}"><i></i>Tandang menang<b>{_koma(tandang)}%</b></span>
      </div>
    </div>
  </div>'''
    kartu = [
        (f"{_koma(f['unggul_jeda_menang'])}%", "Unggul saat jeda, biasanya menang",
         "Tim yang memimpin di babak pertama akhirnya menang di tiga dari empat laga."),
        (f"{_koma(f['gol_babak2'])}%", "Gol lebih banyak di babak kedua",
         "Lebih dari separuh gol tercipta setelah jeda, ketika stamina turun dan pemain pengganti masuk."),
        (f"{f['skor_umum']} gol", "Total skor paling sering",
         f"{_koma(f['skor_umum_persen'])}% laga berakhir dengan total {f['skor_umum']} gol; "
         f"rata-rata {_koma(f['gol_per_laga'], 2)} gol per laga."),
        (f"{_koma(f['konversi'])}%", "Tembakan yang jadi gol",
         "Hanya sekitar satu dari sembilan tembakan berbuah gol. Ketajaman membedakan klub papan atas."),
        (f"{_koma(f['langgar_awal'])} → {_koma(f['langgar_akhir'])}", "Permainan makin bersih",
         f"Pelanggaran per tim per laga turun dari musim {f['musim_penuh_awal']} ke {f['musim_penuh_akhir']}."),
        (f"{f['gelar']} gelar", f"{escape(f['juara'])} paling sering juara",
         f"Dari {f['musim_selesai']} musim yang sudah selesai, gelar terkumpul di segelintir klub."),
    ]
    isi = "".join(
        f'<div class="lp-insight lp-muncul"><b>{angka}</b><h3>{judul}</h3><p>{teks}</p></div>'
        for angka, judul, teks in kartu
    )
    return f'''
<section class="lp-bagian" id="insight">
  <div class="lp-kepala lp-muncul">
    <h2>Key Insight</h2>
    <p>Temuan utama dari {f["musim"]} musim data, semuanya bisa ditelusuri lagi di dashboard.</p>
  </div>
  {utama}
  <div class="lp-insight-grid">{isi}</div>
</section>'''


def _kaki() -> str:
    return '''
<footer class="lp-kaki">
  <span>BallBoard, tugas akhir Pengantar Sains Data oleh Kelompok 8.</span>
  <span>Data: football-data.co.uk, API-Football, BBC Sport, openfootball.</span>
</footer>'''


def tampil() -> None:
    df = muat_pertandingan(str(JALUR_DATA))
    f = fakta(df)
    perbandingan, metrik = _model()
    logo = _uri_logo(str(AKAR / "data" / "ballboard_logo.png"))
    lambang = _uri_logo(str(AKAR / "data" / "ballboard_lambang_besar.png"))
    _panaskan_modul(df)
    st.markdown(f"<style>{_CSS.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
    st.markdown(
        '<div class="landing">'
        + _nav(logo) + _hero(f, lambang) + _overview() + _dataset(f) + _praproses(f)
        + _modelling(perbandingan, metrik) + _insight(f) + _kaki()
        + "</div>",
        unsafe_allow_html=True,
    )
