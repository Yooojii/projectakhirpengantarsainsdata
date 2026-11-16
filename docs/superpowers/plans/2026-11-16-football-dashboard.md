# Dashboard Liga Inggris — Rencana Implementasi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun dashboard Streamlit empat halaman untuk pelatih Liga Inggris yang memprediksi hasil pertandingan dan menyediakan ruang simulasi berbasis atribut pemain, sekaligus mencakup tujuh poin rubrik UAS.

**Architecture:** Lapisan inti murni Python tanpa Streamlit (`inti/`) sehingga semuanya bisa diuji tanpa menjalankan aplikasi; lapisan tampilan (`halaman/`, `gaya/`) hanya memanggil lapisan inti. `inti/fitur.py` adalah satu-satunya sumber kebenaran perhitungan fitur dan diimpor oleh pipeline pelatihan rekan kelompok. Simulasi bekerja dengan membangkitkan skuad terkalibrasi, lalu menerjemahkannya kembali menjadi vektor fitur yang sama bentuknya dengan yang dipakai model.

**Tech Stack:** Python 3.13, Streamlit 1.55, pandas 2.3, numpy 2.3, Altair 6.0, scipy 1.17, joblib 1.5, pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-football-dashboard-design.md`

## Global Constraints

- Seluruh antarmuka berbahasa Indonesia. Istilah statistik diterjemahkan ke bahasa pelatih: "peluang menang", "gol yang diharapkan", "apa yang paling menentukan".
- Model hanya boleh memakai sepuluh fitur dasar di spec §8.2. Odds, statistik API, `xg_kandang`, dan `xg_tandang` dilarang sebagai fitur.
- Angka buatan hanya di lapisan pemain dan jadwal. Statistik lanjutan dan 45 laga hilang di 2003/04–2004/05 dibiarkan apa adanya (spec §7.7).
- Warna, nilai tepat: latar `#F4F6F2`, teks utama `#0E1F18`, teks sekunder `#6B7A72`, garis `#CFD6CC`, permukaan `#FFFFFF`, peringatan `#E0A800`, bahaya `#C8102E`. Aksen diambil dari klub terpilih.
- Tipografi: IBM Plex Sans untuk prosa, IBM Plex Sans Condensed untuk angka dan tabel. Papan skor 64px/600, nama klub 24px/500, judul bagian 22px/600, prosa 16px/1.6 maksimal 68 karakter per baris, label 13px, angka tabel 15px/500.
- Jarak kelipatan 8px; antarbagian 48px, dalam bagian 16px. Sudut membulat 4px seragam. **Tanpa bayangan sama sekali.**
- Tema terang dikunci. Tidak ada mode gelap.
- Dilarang: label huruf kapital seluruhnya, ikon di navigasi, animasi masuk halaman, efek saat kursor melewati kartu, gradien, emoji, dan tanda panah di teks tombol.
- Judul grafik ditulis sebagai kalimat temuan, bukan nama variabel.
- Benih acak pembangkit skuad dikunci agar hasilnya sama setiap kali dibuka.
- Semua tren per musim memakai ukuran per laga, bukan jumlah total (spec §6.4).
- Waktu disebut dengan tanggal, bukan nomor pekan (spec §6.5).

## Review Focus

1. **Klub dengan riwayat sangat tipis.** Coventry hanya punya 47 laga di dataset dan jendela sepuluh laganya menjangkau 19 Mei 2001. Fitur harus tetap terhitung, bukan melempar galat. Tes di Task 3.
2. **Pasangan klub yang belum pernah bertemu.** Enam pasangan di musim berjalan punya nol pertemuan. Halaman History harus menampilkan keadaan kosong, bukan tabel kosong atau galat. Tes di Task 12.
3. **Berkas model belum ada.** Scraping dan pemodelan rekan kelompok belum selesai, jadi `model/model.joblib` kemungkinan besar belum ada saat dashboard pertama dijalankan. Seluruh aplikasi harus tetap hidup lewat jalan mundur Poisson. Tes di Task 6.
4. **CSV ditukar dengan hasil scraping yang lebih lengkap.** Bagian EDA yang tidur harus bangun sendiri saat cakupan kolom lewat 60%, dan tidak ada yang rusak ketika jumlah baris bertambah. Tes di Task 11.
5. **Gol harapan nol atau mendekati nol.** Atribut digeser ke nilai terendah bisa menghasilkan gol harapan nol; distribusi Poisson harus tetap menghasilkan peluang yang sah tanpa NaN atau pembagian nol. Tes di Task 6.

---

### Task 1: Fondasi proyek dan pemuatan data

**Files:**
- Create: `requirements.txt`, `.gitignore`, `conftest.py`, `inti/__init__.py`, `inti/data.py`
- Test: `tests/test_data.py`

**Interfaces:**
- Consumes: —
- Produces:
  - `muat_pertandingan(path: str = "data/liga_inggris_gabungan.csv") -> pd.DataFrame` — kolom `tanggal` bertipe datetime64, diurutkan menaik, indeks direset.
  - `cakupan_kolom(df: pd.DataFrame) -> pd.DataFrame` — kolom `kelompok`, `kolom`, `terisi`, `persen`.
  - `KELOMPOK_KOLOM: dict[str, list[str]]` — lima kelompok: `identitas`, `hasil`, `statistik_dasar`, `odds`, `statistik_lanjutan`.
  - `klub_musim(df: pd.DataFrame, musim: str) -> list[str]` — urut abjad.

- [ ] **Step 1: Inisialisasi repo dan dependensi**

```bash
git init
printf '__pycache__/\n*.pyc\n.pytest_cache/\n.venv/\nmodel/*.joblib\n' > .gitignore
printf 'streamlit>=1.55\npandas>=2.3\nnumpy>=2.3\naltair>=6.0\nscipy>=1.17\njoblib>=1.5\npytest>=8.0\n' > requirements.txt
pip install pytest
touch conftest.py          # kosong, tapi wajib: tanpa ini pytest tidak menaruh
                           # akar proyek di sys.path dan `from inti...` gagal
mkdir -p inti halaman gaya tests model
touch inti/__init__.py
```

- [ ] **Step 2: Tulis tes yang gagal**

```python
# tests/test_data.py
import pandas as pd
from inti.data import muat_pertandingan, cakupan_kolom, KELOMPOK_KOLOM, klub_musim

def test_muat_pertandingan_bentuk_dan_tipe():
    df = muat_pertandingan()
    assert df.shape == (9880, 56)
    assert pd.api.types.is_datetime64_any_dtype(df["tanggal"])
    assert df["tanggal"].is_monotonic_increasing

def test_kelompok_kolom_mencakup_semua_kolom_tanpa_tumpang_tindih():
    df = muat_pertandingan()
    semua = [k for kolom in KELOMPOK_KOLOM.values() for k in kolom]
    assert len(semua) == len(set(semua))
    assert set(semua) == set(df.columns)

def test_cakupan_xg_musim_berjalan_terpisah_dari_statistik_api():
    df = muat_pertandingan()
    cak = cakupan_kolom(df).set_index("kolom")
    assert cak.loc["xg_kandang", "terisi"] == 90
    assert cak.loc["xg_api_kandang", "terisi"] == 102
    assert cak.loc["xg_kandang", "kelompok"] == "statistik_lanjutan"
    assert cak.loc["tembakan_kandang", "persen"] == 100.0

def test_klub_musim_berjalan_ada_dua_puluh():
    klub = klub_musim(muat_pertandingan(), "2026/27")
    assert len(klub) == 20
    assert klub[0] == "Arsenal"
    assert "Coventry" in klub
```

- [ ] **Step 3: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_data.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'inti'`

- [ ] **Step 4: Implementasikan `inti/data.py`**

`muat_pertandingan` memakai `pd.read_csv` dengan `parse_dates=["tanggal"]`, lalu `sort_values("tanggal").reset_index(drop=True)`. Beri dekorator `@st.cache_data` hanya kalau Streamlit tersedia — bungkus impornya dengan `try/except ImportError` supaya modul inti tetap bisa diuji tanpa Streamlit.

`KELOMPOK_KOLOM` ditulis tangan dan harus menampung seluruh 56 kolom. `xg_kandang` dan `xg_tandang` masuk `statistik_lanjutan`, terpisah dari `xg_api_*` yang juga di sana.

- [ ] **Step 5: Jalankan tes, pastikan lulus**

Run: `python -m pytest tests/test_data.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt inti/ tests/ data/ docs/
git commit -m "feat: pemuatan data dan pengelompokan kolom"
```

---

### Task 2: Identitas klub

**Files:**
- Create: `inti/klub.py`
- Test: `tests/test_klub.py`

**Interfaces:**
- Consumes: `klub_musim` dari Task 1.
- Produces:
  - `warna_klub(nama: str) -> str` — hex. Klub tak dikenal mengembalikan `"#6B7A72"`.
  - `singkatan(nama: str) -> str` — tiga huruf kapital untuk tabel sempit.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_klub.py
from inti.data import muat_pertandingan, klub_musim
from inti.klub import warna_klub, singkatan

def test_semua_klub_musim_berjalan_punya_warna():
    for nama in klub_musim(muat_pertandingan(), "2026/27"):
        assert warna_klub(nama).startswith("#") and len(warna_klub(nama)) == 7

def test_klub_tak_dikenal_dapat_warna_netral():
    assert warna_klub("Klub Antah Berantah") == "#6B7A72"

def test_singkatan_tiga_huruf():
    assert singkatan("Man United") == "MUN"
    assert singkatan("Nott'm Forest") == "NFO"
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_klub.py -v`
Expected: FAIL, modul `inti.klub` belum ada

- [ ] **Step 3: Implementasikan `inti/klub.py`**

Satu dict `WARNA` berisi 46 klub yang pernah muncul di dataset, memakai warna utama tiap klub. Satu dict `SINGKATAN` untuk kasus yang tidak bisa diturunkan otomatis; sisanya diturunkan dari tiga huruf pertama nama yang dikapitalkan.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `python -m pytest tests/test_klub.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add inti/klub.py tests/test_klub.py
git commit -m "feat: identitas dan warna klub"
```

---

### Task 3: Perhitungan fitur — sumber kebenaran tunggal

Ini modul yang diimpor rekan pemodelan untuk membangun tabel pelatihannya (spec §8.2). Definisinya tidak boleh ditulis dua kali.

**Files:**
- Create: `inti/fitur.py`
- Test: `tests/test_fitur.py`

**Interfaces:**
- Consumes: `muat_pertandingan` dari Task 1.
- Produces:
  - `NAMA_FITUR: list[str]` — sepuluh nama, urutan tetap: `rata_tembakan`, `rata_tembakan_tepat`, `rasio_konversi`, `rata_sepak_pojok`, `rata_pelanggaran`, `rata_kartu_kuning`, `rata_gol_dicetak`, `rata_gol_kebobolan`, `poin_lima_laga`, `penanda_kandang`.
  - `fitur_tim(df: pd.DataFrame, klub: str, sebelum: pd.Timestamp, kandang: bool) -> dict[str, float]` — kunci persis `NAMA_FITUR`.
  - `tabel_pelatihan(df: pd.DataFrame) -> pd.DataFrame` — satu baris per laga, fitur kandang berakhiran `_k` dan tandang `_t`, ditambah kolom `hasil`. Baris yang klubnya punya kurang dari tiga laga sebelumnya dibuang.

- [ ] **Step 1: Tulis tes yang gagal**

Nilai acuan di bawah dihitung langsung dari CSV dan harus cocok persis.

```python
# tests/test_fitur.py
import pandas as pd, pytest
from inti.data import muat_pertandingan
from inti.fitur import NAMA_FITUR, fitur_tim, tabel_pelatihan

@pytest.fixture(scope="module")
def df():
    return muat_pertandingan()

def test_sepuluh_fitur_dengan_urutan_tetap():
    assert len(NAMA_FITUR) == 10
    assert NAMA_FITUR[0] == "rata_tembakan"
    assert NAMA_FITUR[-1] == "penanda_kandang"

def test_nilai_acuan_arsenal_akhir_musim(df):
    f = fitur_tim(df, "Arsenal", pd.Timestamp("2026-11-03"), kandang=True)
    assert f["rata_gol_dicetak"] == pytest.approx(1.6)
    assert f["rata_tembakan"] == pytest.approx(13.4)
    assert f["rasio_konversi"] == pytest.approx(16.0 / 134.0)
    assert f["penanda_kandang"] == 1.0

def test_konversi_adalah_jumlah_dibagi_jumlah_bukan_rata_rata_rasio(df):
    f = fitur_tim(df, "Arsenal", pd.Timestamp("2026-11-03"), kandang=True)
    assert f["rasio_konversi"] == pytest.approx(f["rata_gol_dicetak"] / f["rata_tembakan"])

def test_jendela_melintasi_batas_musim_untuk_klub_promosi(df):
    # Coventry hanya punya 47 laga, laga ke-10 dari belakang jatuh 2001
    f = fitur_tim(df, "Coventry", pd.Timestamp("2026-11-03"), kandang=False)
    assert all(k in f for k in NAMA_FITUR)
    assert f["rata_tembakan"] > 0

def test_laga_yang_diprediksi_tidak_ikut_dihitung(df):
    sebelum = fitur_tim(df, "Arsenal", pd.Timestamp("2026-11-01"), kandang=True)
    sesudah = fitur_tim(df, "Arsenal", pd.Timestamp("2026-11-02"), kandang=True)
    assert sebelum != sesudah  # laga 1 Nov masuk hanya pada panggilan kedua

def test_poin_lima_laga_dalam_rentang_nol_sampai_lima_belas(df):
    f = fitur_tim(df, "Man City", pd.Timestamp("2026-11-03"), kandang=True)
    assert 0 <= f["poin_lima_laga"] <= 15

def test_klub_tanpa_riwayat_memakai_rata_rata_liga(df):
    f = fitur_tim(df, "Arsenal", pd.Timestamp("2000-08-20"), kandang=True)
    assert all(k in f for k in NAMA_FITUR)
    assert f["rata_tembakan"] > 0

def test_tabel_pelatihan_tidak_mengandung_odds_atau_statistik_lanjutan(df):
    t = tabel_pelatihan(df)
    terlarang = ["odds", "xg", "penguasaan", "umpan", "offside", "penyelamatan"]
    assert not [c for c in t.columns if any(x in c for x in terlarang)]
    assert len(t) > 9000
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_fitur.py -v`
Expected: FAIL, modul `inti.fitur` belum ada

- [ ] **Step 3: Implementasikan `inti/fitur.py`**

Aturan jendela dikunci di spec §8.2 dan harus diikuti persis: sepuluh laga terakhir klub itu kandang dan tandang digabung, diurutkan menurut tanggal, melintasi batas musim, **tidak termasuk laga yang tanggalnya sama dengan atau sesudah** `sebelum`. Kurang dari sepuluh laga memakai yang ada dengan minimum tiga; di bawah tiga memakai rata-rata liga pada musim itu.

Perhatikan: untuk tiap laga dalam jendela, statistik klub diambil dari kolom berakhiran `_kandang` atau `_tandang` tergantung klub itu bertindak sebagai tuan rumah atau tamu pada laga tersebut — bukan tergantung argumen `kandang`, yang hanya mengisi `penanda_kandang` untuk laga yang sedang diprediksi.

`rasio_konversi` adalah jumlah gol sepuluh laga dibagi jumlah tembakan sepuluh laga.

`tabel_pelatihan` membangun satu baris per laga dengan memanggil `fitur_tim` dua kali. Pada 9.880 laga ini akan lambat kalau naif; gunakan pengurutan sekali dan jendela bergulir per klub.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `python -m pytest tests/test_fitur.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add inti/fitur.py tests/test_fitur.py
git commit -m "feat: perhitungan fitur sebagai sumber kebenaran tunggal"
```

---

### Task 4: Pembangkit dan kalibrasi skuad

**Files:**
- Create: `inti/pemain.py`
- Test: `tests/test_pemain.py`

**Interfaces:**
- Consumes: `fitur_tim`, `NAMA_FITUR` dari Task 3.
- Produces:
  - `ATRIBUT: list[str]` — `penyelesaian`, `kreativitas`, `penguasaan`, `rebutan`, `antisipasi`, `ketenangan`. Kiper menambah `refleks`.
  - `@dataclass Pemain` — `nama: str`, `posisi: str` (`"KIP"`, `"BEL"`, `"TEN"`, `"DEP"`), `atribut: dict[str, int]`, `inti: bool`.
  - `bangkitkan_skuad(df, klub: str, sebelum: pd.Timestamp) -> list[Pemain]` — 11 inti berformasi 4-3-3 ditambah 7 cadangan.
  - `BENIH: int = 2627`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_pemain.py
import pandas as pd, pytest
from inti.data import muat_pertandingan
from inti.pemain import bangkitkan_skuad, ATRIBUT

TGL = pd.Timestamp("2026-11-03")

@pytest.fixture(scope="module")
def df():
    return muat_pertandingan()

def test_skuad_sebelas_inti_dan_tujuh_cadangan(df):
    s = bangkitkan_skuad(df, "Arsenal", TGL)
    assert len([p for p in s if p.inti]) == 11
    assert len([p for p in s if not p.inti]) == 7

def test_formasi_empat_tiga_tiga(df):
    inti = [p for p in bangkitkan_skuad(df, "Arsenal", TGL) if p.inti]
    hitung = {p.posisi: sum(1 for q in inti if q.posisi == p.posisi) for p in inti}
    assert hitung == {"KIP": 1, "BEL": 4, "TEN": 3, "DEP": 3}

def test_hasil_sama_setiap_dipanggil(df):
    a = bangkitkan_skuad(df, "Arsenal", TGL)
    b = bangkitkan_skuad(df, "Arsenal", TGL)
    assert [(p.nama, p.atribut) for p in a] == [(p.nama, p.atribut) for p in b]

def test_atribut_dalam_rentang_satu_sampai_sembilan_puluh_sembilan(df):
    for p in bangkitkan_skuad(df, "Man City", TGL):
        for a in ATRIBUT:
            assert 1 <= p.atribut[a] <= 99

def test_klub_berkonversi_lebih_baik_punya_penyelesaian_lebih_tinggi(df):
    from inti.fitur import fitur_tim
    pasangan = [(k, fitur_tim(df, k, TGL, True)["rasio_konversi"]) for k in ["Man City", "Arsenal", "Everton", "Hull"]]
    pasangan.sort(key=lambda x: x[1])
    terburuk, terbaik = pasangan[0][0], pasangan[-1][0]
    def depan(k):
        s = [p for p in bangkitkan_skuad(df, k, TGL) if p.inti and p.posisi == "DEP"]
        return sum(p.atribut["penyelesaian"] for p in s) / len(s)
    assert depan(terbaik) > depan(terburuk)

def test_kiper_punya_refleks(df):
    kip = [p for p in bangkitkan_skuad(df, "Arsenal", TGL) if p.posisi == "KIP"]
    assert all("refleks" in p.atribut for p in kip)

def test_klub_dengan_riwayat_tipis_tetap_dapat_skuad(df):
    assert len(bangkitkan_skuad(df, "Coventry", TGL)) == 18
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_pemain.py -v`
Expected: FAIL, modul `inti.pemain` belum ada

- [ ] **Step 3: Implementasikan `inti/pemain.py`**

Untuk tiap atribut, hitung persentil klub di dalam liga pada metrik terkait (spec §7.2 memetakan atribut ke metrik), lalu petakan persentil 0–1 ke pusat sebaran 45–85. Tiap pemain mendapat simpangan menurut posisinya: penyerang digeser naik pada `penyelesaian`, bek pada `antisipasi` dan `rebutan`, gelandang pada `kreativitas` dan `penguasaan`. Cadangan digeser turun 6 poin. Semua keacakan memakai `numpy.random.default_rng` yang dibenihi dari `BENIH` dan nama klub, supaya hasilnya tetap sama antar sesi dan berbeda antar klub.

Nama pemain dibangkitkan dari daftar nama depan dan belakang bergaya Inggris dan Eropa, dibenihi sama. Bukan nama pemain sungguhan (spec §7.5).

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `python -m pytest tests/test_pemain.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add inti/pemain.py tests/test_pemain.py
git commit -m "feat: pembangkit skuad terkalibrasi dari statistik tim"
```

---

### Task 5: Agregasi pemain kembali ke fitur

Inti kejujuran proyek. Janji di spec §7.1 ditegakkan oleh tes pertama di bawah.

**Files:**
- Create: `inti/agregasi.py`
- Test: `tests/test_agregasi.py`

**Interfaces:**
- Consumes: `fitur_tim`, `NAMA_FITUR` (Task 3); `Pemain`, `bangkitkan_skuad` (Task 4).
- Produces:
  - `kalibrasi(df, klub: str, sebelum: pd.Timestamp) -> dict[str, float]` — konstanta penskalaan per fitur, dipasang sekali per klub.
  - `agregasi_fitur(skuad: list[Pemain], skuad_lawan: list[Pemain], konst: dict[str, float], poin_lima_laga: float, kandang: bool) -> dict[str, float]` — kunci persis `NAMA_FITUR`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_agregasi.py
import pandas as pd, pytest
from inti.data import muat_pertandingan
from inti.fitur import fitur_tim, NAMA_FITUR
from inti.pemain import bangkitkan_skuad
from inti.agregasi import kalibrasi, agregasi_fitur

TGL = pd.Timestamp("2026-11-03")

@pytest.fixture(scope="module")
def df():
    return muat_pertandingan()

def siapkan(df, klub, lawan, kandang=True):
    asli = fitur_tim(df, klub, TGL, kandang)
    s, sl = bangkitkan_skuad(df, klub, TGL), bangkitkan_skuad(df, lawan, TGL)
    k = kalibrasi(df, klub, TGL)
    return asli, s, sl, k

@pytest.mark.parametrize("klub,lawan", [("Arsenal", "Tottenham"), ("Hull", "Man City"), ("Coventry", "Liverpool")])
def test_titik_nol_mereproduksi_fitur_nyata(df, klub, lawan):
    """Spec 7.1: penggeser di posisi awal harus menghasilkan fitur yang sama persis."""
    asli, s, sl, k = siapkan(df, klub, lawan)
    hasil = agregasi_fitur(s, sl, k, asli["poin_lima_laga"], kandang=True)
    for nama in NAMA_FITUR:
        assert hasil[nama] == pytest.approx(asli[nama], rel=1e-9)

def geser(skuad, atribut, delta):
    import copy
    s = copy.deepcopy(skuad)
    for p in s:
        if atribut in p.atribut:
            p.atribut[atribut] = max(1, min(99, p.atribut[atribut] + delta))
    return s

@pytest.mark.parametrize("atribut,fitur,naik", [
    ("penyelesaian", "rasio_konversi", True),
    ("kreativitas", "rata_tembakan", True),
    ("kreativitas", "rata_sepak_pojok", True),
    ("rebutan", "rata_pelanggaran", True),
    ("ketenangan", "rata_kartu_kuning", False),
])
def test_arah_pergerakan_tiap_atribut(df, atribut, fitur, naik):
    asli, s, sl, k = siapkan(df, "Arsenal", "Tottenham")
    awal = agregasi_fitur(s, sl, k, asli["poin_lima_laga"], True)[fitur]
    akhir = agregasi_fitur(geser(s, atribut, 10), sl, k, asli["poin_lima_laga"], True)[fitur]
    assert akhir > awal if naik else akhir < awal

def test_antisipasi_lawan_menurunkan_gol_kebobolan_kita(df):
    asli, s, sl, k = siapkan(df, "Arsenal", "Tottenham")
    awal = agregasi_fitur(s, sl, k, asli["poin_lima_laga"], True)["rata_gol_kebobolan"]
    akhir = agregasi_fitur(geser(s, "antisipasi", 10), sl, k, asli["poin_lima_laga"], True)["rata_gol_kebobolan"]
    assert akhir < awal

def test_gol_dicetak_adalah_turunan_bukan_dihitung_langsung(df):
    """Spec 7.4: gol dicetak = konversi x tembakan, supaya tidak dihitung dua kali."""
    asli, s, sl, k = siapkan(df, "Arsenal", "Tottenham")
    h = agregasi_fitur(geser(s, "penyelesaian", 15), sl, k, asli["poin_lima_laga"], True)
    assert h["rata_gol_dicetak"] == pytest.approx(h["rasio_konversi"] * h["rata_tembakan"])
    assert h["rata_tembakan_tepat"] <= h["rata_tembakan"]

def test_bentuk_permainan_dibekukan(df):
    asli, s, sl, k = siapkan(df, "Arsenal", "Tottenham")
    h = agregasi_fitur(geser(s, "penyelesaian", 20), sl, k, asli["poin_lima_laga"], True)
    assert h["poin_lima_laga"] == asli["poin_lima_laga"]

def test_cadangan_tidak_berpengaruh(df):
    asli, s, sl, k = siapkan(df, "Arsenal", "Tottenham")
    awal = agregasi_fitur(s, sl, k, asli["poin_lima_laga"], True)
    import copy
    diubah = copy.deepcopy(s)
    for p in diubah:
        if not p.inti:
            p.atribut["penyelesaian"] = 99
    assert agregasi_fitur(diubah, sl, k, asli["poin_lima_laga"], True) == awal
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_agregasi.py -v`
Expected: FAIL, modul `inti.agregasi` belum ada

- [ ] **Step 3: Implementasikan `inti/agregasi.py`**

Bentuk tiap fitur langsung: `nilai = konst[fitur] * rata_tertimbang_atribut(skuad)`, dengan bobot posisi yang memberi lini depan pengaruh terbesar pada serangan dan lini belakang pada pertahanan. `kalibrasi` menghitung `konst[fitur] = fitur_nyata / rata_tertimbang_atribut(skuad_awal)`, sehingga identitas di tes pertama berlaku menurut konstruksi.

Fitur turunan tidak boleh punya konstanta sendiri: `rata_gol_dicetak = rasio_konversi * rata_tembakan`, dan `rata_tembakan_tepat = rata_tembakan * proporsi` dengan proporsi dari `penyelesaian`. `rata_gol_kebobolan` dihitung dari atribut bertahan skuad sendiri — `antisipasi`, `rebutan`, dan `refleks` kiper. `poin_lima_laga` diteruskan apa adanya dari argumen. `penanda_kandang` dari argumen `kandang`.

Hanya pemain `inti` yang masuk hitungan.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `python -m pytest tests/test_agregasi.py -v`
Expected: 13 passed

- [ ] **Step 5: Commit**

```bash
git add inti/agregasi.py tests/test_agregasi.py
git commit -m "feat: agregasi pemain ke fitur dengan titik nol terkalibrasi"
```

---

### Task 6: Model, prediksi, dan distribusi skor

**Files:**
- Create: `inti/model.py`
- Test: `tests/test_model.py`

**Interfaces:**
- Consumes: `NAMA_FITUR` dari Task 3.
- Produces:
  - `muat_model(path: str = "model/model.joblib") -> object | None` — `None` kalau berkas tidak ada.
  - `prediksi(fitur_k: dict, fitur_t: dict, model=None) -> dict` — kunci `p_menang_kandang`, `p_seri`, `p_menang_tandang`, `gol_harapan_kandang`, `gol_harapan_tandang`. Tanpa model, memakai jalan mundur Poisson (spec §8.6).
  - `distribusi_skor(gol_k: float, gol_t: float, maks: int = 6) -> dict[tuple[int, int], float]`
  - `skor_utama(dist: dict, hasil: str) -> tuple[int, int]` — `hasil` salah satu `"H"`, `"D"`, `"A"`; mengembalikan skor paling mungkin **di dalam** hasil itu (spec §6.6).
  - `muat_evaluasi(path: str = "model/metrik.json") -> dict | None`
  - `pembanding(prediksi_uji: pd.DataFrame) -> dict[str, float]` — kunci `model`, `selalu_kandang`, `ikut_odds`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_model.py
import pytest
from inti.model import muat_model, prediksi, distribusi_skor, skor_utama

def test_tanpa_berkas_model_tetap_memprediksi():
    """Review focus 3: berkas model rekan kelompok kemungkinan belum ada."""
    assert muat_model("model/tidak_ada.joblib") is None
    h = prediksi({"rata_gol_dicetak": 1.8, "rata_gol_kebobolan": 1.0, "penanda_kandang": 1.0},
                 {"rata_gol_dicetak": 1.2, "rata_gol_kebobolan": 1.4, "penanda_kandang": 0.0})
    assert h["gol_harapan_kandang"] > h["gol_harapan_tandang"]
    assert h["p_menang_kandang"] > h["p_menang_tandang"]
    assert sum(h[k] for k in ("p_menang_kandang", "p_seri", "p_menang_tandang")) == pytest.approx(1.0)

def test_distribusi_skor_berjumlah_satu():
    d = distribusi_skor(1.6, 1.1)
    assert sum(d.values()) == pytest.approx(1.0, abs=1e-3)
    assert all(v >= 0 for v in d.values())

def test_gol_harapan_nol_tidak_menghasilkan_nan():
    """Review focus 5: atribut digeser ke nilai terendah bisa menghasilkan nol."""
    d = distribusi_skor(0.0, 0.0)
    assert sum(d.values()) == pytest.approx(1.0, abs=1e-3)
    assert d[(0, 0)] == pytest.approx(1.0, abs=1e-3)
    assert not any(v != v for v in d.values())

def test_skor_utama_tidak_pernah_membantah_hasil_terkuat():
    """Spec 6.6: papan tidak boleh menulis 2-1 di atas 'kalah 46%'."""
    d = distribusi_skor(1.2, 1.9)   # Poisson condong ke tamu
    k, t = skor_utama(d, "H")
    assert k > t
    k, t = skor_utama(d, "D")
    assert k == t
    k, t = skor_utama(d, "A")
    assert k < t

def test_pembanding_dihitung_pada_baris_yang_sama():
    import pandas as pd
    from inti.model import pembanding
    uji = pd.DataFrame({
        "hasil": ["H", "A", "D", "H"],
        "prediksi": ["H", "H", "D", "H"],
        "odds_kandang": [1.5, 4.0, 2.0, 1.8],
        "odds_seri": [4.0, 3.5, 3.0, 3.6],
        "odds_tandang": [6.0, 1.9, 3.5, 4.2],
    })
    p = pembanding(uji)
    assert p["model"] == pytest.approx(0.75)
    assert p["selalu_kandang"] == pytest.approx(0.5)
    assert p["ikut_odds"] == pytest.approx(0.5)
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_model.py -v`
Expected: FAIL, modul `inti.model` belum ada

- [ ] **Step 3: Implementasikan `inti/model.py`**

`prediksi` tanpa model: gol harapan kandang diambil dari rata-rata serangan kandang dan pertahanan tamu, dan sebaliknya; peluang hasil dijumlahkan dari `distribusi_skor`. Dengan model: susun vektor menurut urutan `NAMA_FITUR`, panggil `predict_proba`, dan ambil gol harapan dari fitur.

`distribusi_skor` memakai `scipy.stats.poisson.pmf` untuk 0..`maks` di kedua sisi dan mengalikannya. Gol harapan nol sah: `poisson.pmf(0, 0) == 1.0`.

`skor_utama` menyaring distribusi ke skor yang konsisten dengan `hasil`, lalu mengambil yang peluangnya terbesar.

`pembanding`: `ikut_odds` menebak hasil dengan odds terendah di antara tiga.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `python -m pytest tests/test_model.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add inti/model.py tests/test_model.py
git commit -m "feat: prediksi, distribusi skor, dan jalan mundur Poisson"
```

---

### Task 7: Jadwal simulasi sisa musim

**Files:**
- Create: `inti/jadwal.py`
- Test: `tests/test_jadwal.py`

**Interfaces:**
- Consumes: `klub_musim` dari Task 1.
- Produces: `jadwal_sisa(df, musim: str = "2026/27") -> pd.DataFrame` — kolom `tanggal`, `tim_kandang`, `tim_tandang`, mulai Sabtu 7 November 2026.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_jadwal.py
import pandas as pd
from inti.data import muat_pertandingan
from inti.jadwal import jadwal_sisa

def test_melengkapi_setengah_kompetisi_ganda():
    df = muat_pertandingan()
    sisa = jadwal_sisa(df)
    dimainkan = df[df.musim == "2026/27"]
    assert len(sisa) == 380 - len(dimainkan)
    gabung = set(zip(dimainkan.tim_kandang, dimainkan.tim_tandang)) | set(zip(sisa.tim_kandang, sisa.tim_tandang))
    assert len(gabung) == 380

def test_tidak_mengulang_laga_yang_sudah_dimainkan():
    df = muat_pertandingan()
    dimainkan = set(zip(df[df.musim == "2026/27"].tim_kandang, df[df.musim == "2026/27"].tim_tandang))
    assert not dimainkan & set(zip(*[jadwal_sisa(df)[c] for c in ("tim_kandang", "tim_tandang")]))

def test_semua_tanggal_hari_sabtu_mulai_tujuh_november():
    sisa = jadwal_sisa(muat_pertandingan())
    assert sisa.tanggal.min() == pd.Timestamp("2026-11-07")
    assert set(sisa.tanggal.dt.dayofweek) == {5}

def test_tidak_ada_klub_bermain_dua_kali_pada_tanggal_yang_sama():
    sisa = jadwal_sisa(muat_pertandingan())
    for _, hari in sisa.groupby("tanggal"):
        klub = list(hari.tim_kandang) + list(hari.tim_tandang)
        assert len(klub) == len(set(klub))
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_jadwal.py -v`
Expected: FAIL, modul `inti.jadwal` belum ada

- [ ] **Step 3: Implementasikan `inti/jadwal.py`**

Bangun seluruh 380 pasangan berurutan dari 20 klub, buang yang sudah dimainkan, lalu kelompokkan sisanya menjadi putaran maksimal sepuluh laga dengan syarat tidak ada klub muncul dua kali dalam satu putaran. Tetapkan tiap putaran ke hari Sabtu berurutan mulai 7 November 2026.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `python -m pytest tests/test_jadwal.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add inti/jadwal.py tests/test_jadwal.py
git commit -m "feat: pembangkit jadwal simulasi sisa musim"
```

---

### Task 8: Tema dan komponen visual

**Files:**
- Create: `gaya/__init__.py`, `gaya/tema.css`, `gaya/komponen.py`
- Test: `tests/test_komponen.py`

**Interfaces:**
- Consumes: `warna_klub` dari Task 2.
- Produces:
  - `pasang_tema(aksen: str) -> None` — menyuntik CSS sekali, menulis ulang `--aksen`.
  - `papan_skor(klub_k, klub_t, skor, peluang: dict, aksen: str) -> str` — HTML.
  - `bar_atribut(nilai: int, aksen: str | None) -> str` — delapan ruas; `None` berarti abu-abu.
  - `grafik_dasar(data, x, y, judul: str, sorot: str | None, aksen: str) -> alt.Chart`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_komponen.py
from gaya.komponen import papan_skor, bar_atribut, BACA_CSS

def test_css_memuat_token_warna_dan_tanpa_bayangan():
    css = BACA_CSS()
    for warna in ["#F4F6F2", "#0E1F18", "#6B7A72", "#CFD6CC", "#E0A800", "#C8102E"]:
        assert warna in css
    assert "box-shadow" not in css.replace("box-shadow: none", "")
    assert "IBM Plex Sans Condensed" in css

def test_papan_skor_memuat_kedua_klub_dan_tiga_peluang():
    h = papan_skor("Arsenal", "Tottenham", (2, 1),
                   {"menang": 0.54, "seri": 0.24, "kalah": 0.22}, "#EF0107")
    assert "Arsenal" in h and "Tottenham" in h
    assert "54" in h and "24" in h and "22" in h
    assert "→" not in h

def test_bar_atribut_delapan_ruas_terisi_proporsional():
    assert bar_atribut(99, "#EF0107").count("ruas") == 8
    assert bar_atribut(99, "#EF0107").count("terisi") > bar_atribut(20, "#EF0107").count("terisi")
    assert "#6B7A72" in bar_atribut(80, None)
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_komponen.py -v`
Expected: FAIL, paket `gaya` belum ada

- [ ] **Step 3: Implementasikan `gaya/tema.css` dan `gaya/komponen.py`**

CSS mengikuti Global Constraints di atas tanpa kecuali. Muat IBM Plex Sans dan IBM Plex Sans Condensed dari Google Fonts. Definisikan token sebagai variabel pada `:root`, termasuk `--aksen` yang ditulis ulang saat klub berganti. Sembunyikan kerangka bawaan Streamlit yang tidak terpakai (menu utama dan footer).

`papan_skor` menyusun tiga kolom — nama kandang rata kanan, skor di tengah di dalam lingkaran, nama tamu rata kiri — dengan satu garis mendatar yang terputus di lingkaran. Lingkaran dan garis dibuat dengan border, bukan gambar.

`grafik_dasar` mengembalikan Altair tanpa bingkai, tanpa kisi vertikal, kisi mendatar `#CFD6CC`. Deret yang disorot memakai `aksen`, sisanya `#CFD6CC`. Parameter `judul` diisi kalimat temuan oleh pemanggil.

- [ ] **Step 4: Jalankan tes, pastikan lulus**

Run: `python -m pytest tests/test_komponen.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add gaya/ tests/test_komponen.py
git commit -m "feat: tema papan taktik dan komponen visual"
```

---

### Task 9: Kerangka aplikasi dan sidebar

**Files:**
- Create: `app.py`, `halaman/__init__.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: Task 1, 2, 8.
- Produces: `HALAMAN: dict[str, callable]` — empat kunci berurutan: `"Overview"`, `"EDA Liga"`, `"History"`, `"Prediksi & Simulasi"`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_app.py
from app import HALAMAN

def test_empat_halaman_dengan_urutan_tetap():
    assert list(HALAMAN) == ["Overview", "EDA Liga", "History", "Prediksi & Simulasi"]

def test_nama_halaman_tanpa_ikon_dan_tanpa_huruf_kapital_seluruhnya():
    import unicodedata
    for nama in HALAMAN:
        assert nama != nama.upper()
        for ch in nama:
            assert unicodedata.category(ch) != "So", f"ikon atau emoji di {nama!r}"
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_app.py -v`
Expected: FAIL, `app` belum ada

- [ ] **Step 3: Implementasikan `app.py`**

`st.set_page_config` dengan tata letak lebar. Sidebar berisi, berurutan: pemilih klub (20 klub musim berjalan), empat tautan halaman sebagai radio tanpa ikon, dan satu baris keterangan cakupan data di kaki. Klub terpilih disimpan di `st.session_state` dan warnanya diteruskan ke `pasang_tema`. Tidak ada header global, logo, atau breadcrumb.

Setiap fungsi halaman diimpor dari `halaman/` dan ditulis sebagai rintisan dulu; Task 10–13 mengisinya.

- [ ] **Step 4: Jalankan tes dan aplikasi**

Run: `python -m pytest tests/test_app.py -v` → 2 passed
Run: `streamlit run app.py --server.headless true` → memuat tanpa galat, empat halaman bisa diklik

- [ ] **Step 5: Commit**

```bash
git add app.py halaman/ tests/test_app.py
git commit -m "feat: kerangka aplikasi, sidebar, dan rute halaman"
```

---

### Task 10: Halaman Overview

Memuat rubrik poin 1, 2, 4, dan spesifikasi poin 5 (spec §6.1, §6.3).

**Files:**
- Create: `halaman/overview.py`
- Test: `tests/test_overview.py`

**Interfaces:**
- Consumes: `cakupan_kolom`, `KELOMPOK_KOLOM` (Task 1); `jadwal_sisa` (Task 7); `prediksi`, `skor_utama`, `distribusi_skor` (Task 6); `papan_skor` (Task 8).
- Produces: `tabel_kelengkapan(df) -> pd.DataFrame` dengan kolom `kelompok`, `cakupan`, `dipakai_model`, `alasan`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_overview.py
from inti.data import muat_pertandingan
from halaman.overview import tabel_kelengkapan

def test_lima_kelompok_dengan_alasan_tertulis():
    t = tabel_kelengkapan(muat_pertandingan())
    assert len(t) == 5
    assert set(t.kelompok) >= {"statistik_dasar", "odds", "statistik_lanjutan"}
    assert t.alasan.str.len().min() > 10

def test_statistik_lanjutan_dinyatakan_tidak_dipakai_model():
    t = tabel_kelengkapan(muat_pertandingan()).set_index("kelompok")
    assert t.loc["statistik_lanjutan", "dipakai_model"] is False
    assert t.loc["odds", "dipakai_model"] is False
    assert t.loc["statistik_dasar", "dipakai_model"] is True

def test_cakupan_statistik_dasar_seratus_persen():
    t = tabel_kelengkapan(muat_pertandingan()).set_index("kelompok")
    assert t.loc["statistik_dasar", "cakupan"] == 100.0
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_overview.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasikan `halaman/overview.py`**

Urutan halaman mengikuti spec §6.3: tanggal, papan skor laga berikutnya klub terpilih dari `jadwal_sisa`, dua paragraf latar belakang berbahasa pelatih, daftar "Yang bisa dijawab di sini", empat angka ringkas data, `tabel_kelengkapan`, lalu dua `st.expander` tertutup — "Bagaimana data dibersihkan" dan "Model yang dipakai dan cara mengujinya".

Blok preprocessing harus menyebutkan: jendela sepuluh laga melintasi batas musim (dengan contoh Coventry sampai Mei 2001), dua musim yang hanya 335 laga, kolom `pekan` yang dibuang, dan alasan odds serta statistik lanjutan tidak dipakai.

Judul proyek muncul sebagai baris kecil di atas tanggal, bukan judul besar.

- [ ] **Step 4: Jalankan tes dan periksa halaman**

Run: `python -m pytest tests/test_overview.py -v` → 3 passed
Run: `streamlit run app.py` → Overview memuat, kedua expander tertutup secara bawaan

- [ ] **Step 5: Commit**

```bash
git add halaman/overview.py tests/test_overview.py
git commit -m "feat: halaman Overview dengan rubrik 1, 2, dan 4"
```

---

### Task 11: Halaman EDA Liga

Rubrik poin 3 (spec §6.4).

**Files:**
- Create: `halaman/eda_liga.py`
- Test: `tests/test_eda.py`

**Interfaces:**
- Consumes: `muat_pertandingan` (Task 1); `grafik_dasar`, `warna_klub` (Task 2, 8).
- Produces:
  - `cukup_lengkap(df, kolom: str, ambang: float = 0.6) -> bool`
  - `tren_per_musim(df, metrik: str) -> pd.DataFrame` — kolom `musim`, `nilai`, `jumlah_laga`, selalu per laga.
  - `BAGIAN: list[dict]` — enam bagian aktif ditambah dua yang tidur, tiap dict punya `judul`, `kolom_syarat`.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_eda.py
import pytest
from inti.data import muat_pertandingan
from halaman.eda_liga import cukup_lengkap, tren_per_musim, BAGIAN

def test_bagian_statistik_lanjutan_tidur_sekarang():
    """Spec 7.7: tidur sampai cakupan lewat 60%."""
    df = muat_pertandingan()
    assert cukup_lengkap(df, "penguasaan_bola_kandang") is False
    assert cukup_lengkap(df, "tembakan_kandang") is True

def test_bagian_bangun_sendiri_saat_cakupan_cukup():
    """Review focus 4: CSV ditukar dengan hasil scraping lebih lengkap."""
    df = muat_pertandingan()
    df.loc[: int(len(df) * 0.7), "penguasaan_bola_kandang"] = 50.0
    assert cukup_lengkap(df, "penguasaan_bola_kandang") is True

def test_delapan_bagian_dua_di_antaranya_bersyarat():
    assert len(BAGIAN) == 8
    assert sum(1 for b in BAGIAN if b["kolom_syarat"]) == 2

def test_tren_memakai_ukuran_per_laga_bukan_total():
    """Spec 6.4: 2003/04 dan 2004/05 hanya 335 laga."""
    t = tren_per_musim(muat_pertandingan(), "poin").set_index("musim")
    assert t.loc["2003/04", "jumlah_laga"] == 335
    assert 0.5 < t.loc["2003/04", "nilai"] < 3.0
    assert abs(t.loc["2003/04", "nilai"] - t.loc["2002/03", "nilai"]) < 0.5

def test_musim_tidak_utuh_ditandai():
    t = tren_per_musim(muat_pertandingan(), "poin")
    tidak_utuh = set(t[t.jumlah_laga < 380].musim)
    assert tidak_utuh == {"2003/04", "2004/05", "2026/27"}
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_eda.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasikan `halaman/eda_liga.py`**

Enam bagian aktif sesuai daftar di spec §6.4, dua bagian tidur dengan `kolom_syarat` diisi `penguasaan_bola_kandang` dan `xg_api_kandang`. Satu `st.slider` rentang musim di atas halaman berlaku untuk semua grafik. Tiap bagian: satu grafik dan satu kalimat temuan; judul grafik adalah kalimat temuan itu. Klub terpilih di sidebar disorot dengan warna aksen, sisanya `#CFD6CC`.

Musim dengan `jumlah_laga < 380` diberi penanda kecil dan catatan kaki yang menyebutkan jumlah laganya.

- [ ] **Step 4: Jalankan tes dan periksa halaman**

Run: `python -m pytest tests/test_eda.py -v` → 5 passed
Run: `streamlit run app.py` → enam bagian tampil, dua bagian lanjutan tidak muncul

- [ ] **Step 5: Commit**

```bash
git add halaman/eda_liga.py tests/test_eda.py
git commit -m "feat: halaman EDA Liga dengan dua bagian yang tidur"
```

---

### Task 12: Halaman History

**Files:**
- Create: `halaman/history.py`
- Test: `tests/test_history.py`

**Interfaces:**
- Consumes: Task 1, 2, 8.
- Produces:
  - `rekor_pertemuan(df, klub_a: str, klub_b: str) -> dict` — `menang`, `seri`, `kalah`, `total`, dari sudut pandang `klub_a`.
  - `keadaan_riwayat(total: int) -> str` — `"kosong"` (0), `"tipis"` (1–3), `"penuh"` (≥4).
  - `klasemen(df, musim: str) -> pd.DataFrame` — kolom `klub`, `main`, `menang`, `seri`, `kalah`, `gol_memasukkan`, `gol_kemasukan`, `selisih`, `poin`; terurut menurun menurut `poin`.
  - `bentuk_permainan(df, klub: str, n: int = 10) -> list[str]`

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_history.py
import pytest
from inti.data import muat_pertandingan
from halaman.history import rekor_pertemuan, keadaan_riwayat, klasemen, bentuk_permainan

@pytest.fixture(scope="module")
def df():
    return muat_pertandingan()

def test_keadaan_kosong_untuk_pasangan_yang_belum_pernah_bertemu(df):
    """Review focus 2: enam pasangan punya nol pertemuan."""
    r = rekor_pertemuan(df, "Brighton", "Hull")
    assert r["total"] == 0
    assert keadaan_riwayat(r["total"]) == "kosong"

def test_keadaan_tipis_di_bawah_empat_pertemuan():
    assert keadaan_riwayat(0) == "kosong"
    assert keadaan_riwayat(3) == "tipis"
    assert keadaan_riwayat(4) == "penuh"

def test_rekor_simetris(df):
    a = rekor_pertemuan(df, "Arsenal", "Tottenham")
    b = rekor_pertemuan(df, "Tottenham", "Arsenal")
    assert a["menang"] == b["kalah"] and a["seri"] == b["seri"] and a["total"] == b["total"]

def test_klasemen_dua_puluh_klub_terurut_poin(df):
    k = klasemen(df, "2026/27")
    assert len(k) == 20
    assert k.poin.is_monotonic_decreasing
    assert k.main.unique().tolist() == [9]

def test_bentuk_permainan_sepuluh_hasil(df):
    b = bentuk_permainan(df, "Arsenal")
    assert len(b) == 10
    assert set(b) <= {"M", "S", "K"}
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_history.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasikan `halaman/history.py`**

Lima bagian sesuai spec §6.5. Dropdown lawan berisi 19 klub lain musim berjalan, bukan 46 klub sepanjang masa.

Tiga keadaan riwayat ditangani persis seperti tabel di spec §6.5: `kosong` mengganti rekor dengan kalimat "Belum pernah bertemu di Liga Inggris." dan menyembunyikan daftar pertemuan, sementara bentuk permainan dan klasemen tetap tampil; `tipis` menampilkan semuanya ditambah baris peringatan berwarna `#E0A800`; `penuh` menampilkan semuanya.

Klasemen diberi keterangan tanggal, bukan nomor pekan: "Klasemen sampai 2 November 2026."

- [ ] **Step 4: Jalankan tes dan periksa halaman**

Run: `python -m pytest tests/test_history.py -v` → 5 passed
Run: `streamlit run app.py` → pilih Brighton lalu Hull, halaman tetap utuh dengan kalimat keadaan kosong

- [ ] **Step 5: Commit**

```bash
git add halaman/history.py tests/test_history.py
git commit -m "feat: halaman History dengan tiga keadaan riwayat"
```

---

### Task 13: Halaman Prediksi & Simulasi

Memuat hasil rubrik poin 5, serta poin 6 dan 7 (spec §6.1, §6.6).

**Files:**
- Create: `halaman/prediksi_simulasi.py`
- Test: `tests/test_prediksi_halaman.py`

**Interfaces:**
- Consumes: Task 3, 4, 5, 6, 7, 8.
- Produces:
  - `siapkan_sesi(df, klub_k, klub_t, tanggal) -> dict` — kunci: `skuad_kandang`, `skuad_tandang`, `skuad_kandang_awal`, `skuad_tandang_awal`, `konst_kandang`, `konst_tandang`, `poin_kandang`, `poin_tandang`. Dicerminkan ke `st.session_state` saat dipanggil dari Streamlit, tapi fungsinya murni dan bisa diuji tanpa Streamlit.
  - `hitung_prediksi(sesi: dict) -> dict` — kunci `prediksi` dari Task 6 ditambah `skor: tuple[int, int]` dan `lima_teratas: list[tuple[tuple[int, int], float]]`.
  - `selisih(awal: dict, sekarang: dict) -> dict` — hanya kunci yang berubah.

- [ ] **Step 1: Tulis tes yang gagal**

```python
# tests/test_prediksi_halaman.py
import pandas as pd, pytest, copy
from inti.data import muat_pertandingan
from halaman.prediksi_simulasi import siapkan_sesi, hitung_prediksi, selisih

TGL = pd.Timestamp("2026-11-07")

@pytest.fixture(scope="module")
def sesi():
    return siapkan_sesi(muat_pertandingan(), "Arsenal", "Tottenham", TGL)

def test_tanpa_perubahan_tidak_ada_selisih(sesi):
    h = hitung_prediksi(sesi)
    assert selisih(h, hitung_prediksi(sesi)) == {}

def test_menaikkan_penyelesaian_menaikkan_peluang_menang(sesi):
    awal = hitung_prediksi(sesi)
    s = copy.deepcopy(sesi)
    for p in s["skuad_kandang"]:
        if p.inti and p.posisi == "DEP":
            p.atribut["penyelesaian"] = min(99, p.atribut["penyelesaian"] + 15)
    akhir = hitung_prediksi(s)
    assert akhir["p_menang_kandang"] > awal["p_menang_kandang"]
    assert akhir["gol_harapan_kandang"] > awal["gol_harapan_kandang"]

def test_skor_besar_konsisten_dengan_peluang_di_bawahnya(sesi):
    h = hitung_prediksi(sesi)
    k, t = h["skor"]
    peluang = {"H": h["p_menang_kandang"], "D": h["p_seri"], "A": h["p_menang_tandang"]}
    terkuat = max(peluang, key=peluang.get)
    assert (k > t) == (terkuat == "H")
    assert (k == t) == (terkuat == "D")
    assert (k < t) == (terkuat == "A")
```

- [ ] **Step 2: Jalankan tes, pastikan gagal**

Run: `python -m pytest tests/test_prediksi_halaman.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasikan `halaman/prediksi_simulasi.py`**

Urutan sesuai spec §6.6: pemilih laga (jadwal simulasi atau pasangan bebas), papan prediksi, lima skor teratas, susunan pemain klub terpilih terbuka dan susunan lawan terlipat, blok selisih yang hanya muncul setelah ada perubahan, tombol "Kembalikan ke susunan asli" yang mengembalikan keduanya, lalu evaluasi model, "Apa yang kami temukan", dan "Rekomendasi untuk pelatih".

Tabel susunan menampilkan sebelas baris dengan satu atribut utama per posisi; atribut lain muncul saat baris dibuka. Penggeser disimpan di `st.session_state` dengan satu salinan nilai awal yang tidak pernah ditulisi.

Fitur `poin_lima_laga` ditampilkan sebagai angka tetap dengan keterangan "Bentuk permainan diambil dari hasil nyata dan tidak bisa diubah."

Di kaki halaman, satu baris permanen: "Atribut pemain adalah data simulasi yang dikalibrasi dari statistik tim, bukan penilaian pemain sungguhan."

Bagian evaluasi membaca `model/metrik.json` dan `model/prediksi_uji.csv`. Kalau keduanya belum ada, tampilkan satu baris: "Evaluasi menunggu model dari proses pemodelan." Jangan menampilkan angka kosong.

- [ ] **Step 4: Jalankan tes dan periksa halaman**

Run: `python -m pytest tests/test_prediksi_halaman.py -v` → 3 passed
Run: `streamlit run app.py` → geser satu atribut, angka prediksi di atas bergerak

- [ ] **Step 5: Commit**

```bash
git add halaman/prediksi_simulasi.py tests/test_prediksi_halaman.py
git commit -m "feat: halaman Prediksi & Simulasi dengan rubrik 5, 6, dan 7"
```

---

### Task 14: Uji penerimaan simulasi

Dua uji wajib di spec §7.4 yang harus lulus sebelum presentasi. Berbeda dari tes Task 5 karena menembus seluruh rantai sampai prediksi akhir.

**Files:**
- Create: `tests/test_penerimaan.py`

**Interfaces:**
- Consumes: Task 13.

- [ ] **Step 1: Tulis tes penerimaan**

```python
# tests/test_penerimaan.py
import pandas as pd, pytest, copy
from inti.data import muat_pertandingan
from halaman.prediksi_simulasi import siapkan_sesi, hitung_prediksi

TGL = pd.Timestamp("2026-11-07")

@pytest.fixture(scope="module")
def sesi():
    return siapkan_sesi(muat_pertandingan(), "Arsenal", "Tottenham", TGL)

def setel(sesi, atribut, nilai):
    s = copy.deepcopy(sesi)
    for p in s["skuad_kandang"]:
        if p.inti and atribut in p.atribut:
            p.atribut[atribut] = nilai
    return s

@pytest.mark.parametrize("atribut,kunci,naik", [
    ("penyelesaian", "gol_harapan_kandang", True),
    ("kreativitas", "gol_harapan_kandang", True),
    ("antisipasi", "gol_harapan_tandang", False),
    ("rebutan", "gol_harapan_tandang", False),
])
def test_uji_arah(sesi, atribut, kunci, naik):
    """Spec 7.4 uji 1: naikkan 10 poin, pastikan bergerak ke arah yang benar."""
    awal = hitung_prediksi(sesi)[kunci]
    s = copy.deepcopy(sesi)
    for p in s["skuad_kandang"]:
        if p.inti and atribut in p.atribut:
            p.atribut[atribut] = min(99, p.atribut[atribut] + 10)
    akhir = hitung_prediksi(s)[kunci]
    assert akhir > awal if naik else akhir < awal

@pytest.mark.parametrize("atribut,kunci", [
    ("penyelesaian", "gol_harapan_kandang"),
    ("kreativitas", "gol_harapan_kandang"),
])
def test_uji_kepekaan_minimal_setengah_gol(sesi, atribut, kunci):
    """Spec 7.4 uji 2: sapuan penuh harus menggeser gol harapan minimal 0,5."""
    rendah = hitung_prediksi(setel(sesi, atribut, 20))[kunci]
    tinggi = hitung_prediksi(setel(sesi, atribut, 95))[kunci]
    assert tinggi - rendah >= 0.5, (
        f"{atribut} hanya menggeser {tinggi - rendah:.3f} gol. "
        "Bobot bentuk permainan dalam model kemungkinan terlalu dominan — "
        "bereskan di sisi model, jangan perbesar pengali di sisi dashboard."
    )
```

- [ ] **Step 2: Jalankan seluruh rangkaian tes**

Run: `python -m pytest -v`
Expected: semua lulus. Kalau `test_uji_kepekaan_minimal_setengah_gol` gagal, **jangan** memperbesar konstanta di `inti/agregasi.py` — itu merusak kalibrasi titik nol di spec §7.1. Laporkan ke rekan pemodelan sesuai spec §7.4.

- [ ] **Step 3: Jalankan aplikasi dari awal sampai akhir**

Run: `streamlit run app.py`
Periksa: keempat halaman memuat; ganti klub di sidebar dan pastikan warna aksen ikut berubah di seluruh halaman; buka History untuk Brighton lawan Hull dan pastikan keadaan kosong tampil; geser satu atribut di Simulasi dan pastikan papan skor bergerak.

- [ ] **Step 4: Commit**

```bash
git add tests/test_penerimaan.py
git commit -m "test: uji arah dan uji kepekaan simulasi"
```

---

## Catatan untuk rekan pemodelan

Setelah Task 3 selesai, `inti/fitur.py` siap dipakai. Pipeline pelatihan mengimpornya, tidak menulis ulang:

```python
from inti.data import muat_pertandingan
from inti.fitur import tabel_pelatihan, NAMA_FITUR

t = tabel_pelatihan(muat_pertandingan())
latih = t[t.tanggal < "2024-08-01"]
uji   = t[t.tanggal >= "2024-08-01"]     # seluruh data uji di 2019/20 ke atas
```

Keluaran yang diharapkan ada tiga berkas, sesuai spec §8.1 dan §8.5: `model/model.joblib`, `model/metrik.json`, `model/prediksi_uji.csv`. Selama ketiganya belum ada, dashboard tetap berjalan memakai jalan mundur Poisson.
