import pandas as pd, pytest
from inti.data import muat_pertandingan
from inti.fitur import NAMA_FITUR, fitur_tim, tabel_pelatihan

@pytest.fixture(scope="module")
def df():
    return muat_pertandingan()

@pytest.fixture(scope="module")
def tabel(df):
    return tabel_pelatihan(df)

def test_sepuluh_fitur_dengan_urutan_tetap():
    assert len(NAMA_FITUR) == 10
    assert NAMA_FITUR[0] == "rata_tembakan"
    assert NAMA_FITUR[-1] == "penanda_kandang"

def test_nilai_acuan_arsenal_akhir_musim(df):
    f = fitur_tim(df, "Arsenal", pd.Timestamp("2026-11-03"), kandang=True)
    assert list(f) == NAMA_FITUR
    assert f["rata_gol_dicetak"] == pytest.approx(1.6)
    assert f["rata_tembakan"] == pytest.approx(13.4)
    assert f["rata_tembakan_tepat"] == pytest.approx(4.5)
    assert f["rata_gol_kebobolan"] == pytest.approx(0.6)
    assert f["poin_lima_laga"] == pytest.approx(12.0)
    assert f["rasio_konversi"] == pytest.approx(16.0 / 134.0)
    assert f["penanda_kandang"] == 1.0

def test_argumen_kandang_hanya_mengubah_penanda(df):
    t = pd.Timestamp("2026-11-03")
    a = fitur_tim(df, "Arsenal", t, kandang=True)
    b = fitur_tim(df, "Arsenal", t, kandang=False)
    assert b["penanda_kandang"] == 0.0
    assert {k: v for k, v in a.items() if k != "penanda_kandang"} == \
           {k: v for k, v in b.items() if k != "penanda_kandang"}

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

def test_tabel_pelatihan_tidak_mengandung_odds_atau_statistik_lanjutan(tabel):
    terlarang = ["odds", "xg", "penguasaan", "umpan", "offside", "penyelamatan"]
    assert not [c for c in tabel.columns if any(x in c for x in terlarang)]
    assert len(tabel) == 9792

def test_tabel_pelatihan_memuat_identitas_di_depan_lalu_fitur_dan_hasil(tabel):
    identitas = ["tanggal", "tim_kandang", "tim_tandang"]
    fitur = [f"{n}_k" for n in NAMA_FITUR] + [f"{n}_t" for n in NAMA_FITUR]
    assert list(tabel.columns) == identitas + fitur + ["hasil"]

def test_tabel_pelatihan_identik_dengan_fitur_tim(df, tabel):
    # Tabel dan fitur_tim harus satu definisi; periksa sampel yang tersebar.
    for i in list(range(0, len(tabel), 997)) + [len(tabel) - 1]:
        b = tabel.iloc[i]
        k = fitur_tim(df, b["tim_kandang"], b["tanggal"], kandang=True)
        t = fitur_tim(df, b["tim_tandang"], b["tanggal"], kandang=False)
        for n in NAMA_FITUR:
            assert b[f"{n}_k"] == pytest.approx(k[n], rel=1e-9)
            assert b[f"{n}_t"] == pytest.approx(t[n], rel=1e-9)

def test_tabel_pelatihan_membuang_laga_klub_dengan_kurang_dari_tiga_riwayat(df, tabel):
    assert len(tabel) < len(df)
    assert tabel["tanggal"].min() > df["tanggal"].min()

def test_rata_rata_liga_tidak_memakai_laga_setelah_tanggal_prediksi(df):
    # Blackpool: promosi 2010, hanya 2 laga sebelum 2010-08-28 -> cabang rata-rata liga aktif.
    # (Luton tak dipakai di sini: frame terpotong tak memuatnya sama sekali -> ValueError.)
    sebelum = pd.Timestamp("2010-08-28")
    riwayat = df[((df.tim_kandang == "Blackpool") | (df.tim_tandang == "Blackpool")) & (df.tanggal < sebelum)]
    assert 0 < len(riwayat) < 3
    penuh = fitur_tim(df, "Blackpool", sebelum, kandang=True)
    dipotong = fitur_tim(df[df.tanggal < sebelum].copy(), "Blackpool", sebelum, kandang=True)
    assert penuh == dipotong

def test_cold_start_sebelum_laga_pertama_dataset_mengembalikan_fitur_lengkap(df):
    f = fitur_tim(df, "Arsenal", df["tanggal"].min(), kandang=True)
    assert list(f) == NAMA_FITUR
    assert f["rata_tembakan"] > 0 and f["rasio_konversi"] > 0

def test_rata_rata_liga_dibatasi_380_laga_terakhir(df):
    from inti.fitur import LAGA_LIGA
    sebelum = pd.Timestamp("2023-08-12")  # Luton tanpa riwayat; >380 laga sebelumnya
    assert (df.tanggal < sebelum).sum() > LAGA_LIGA
    terpotong = df[df.tanggal < sebelum].tail(LAGA_LIGA)
    kandang = terpotong
    harapan = {
        "rata_tembakan": (kandang.tembakan_kandang.sum() + kandang.tembakan_tandang.sum()) / (2 * LAGA_LIGA),
        "rata_gol_dicetak": (kandang.gol_kandang.sum() + kandang.gol_tandang.sum()) / (2 * LAGA_LIGA),
    }
    f = fitur_tim(df, "Luton", sebelum, kandang=True)
    for k, v in harapan.items():
        assert f[k] == pytest.approx(v)
    semua = df[df.tanggal < sebelum]
    assert f["rata_tembakan"] != pytest.approx(
        (semua.tembakan_kandang.sum() + semua.tembakan_tandang.sum()) / (2 * len(semua)))

def test_klub_tidak_dikenal_memunculkan_valueerror(df):
    with pytest.raises(ValueError, match="Arsenall"):
        fitur_tim(df, "Arsenall", pd.Timestamp("2026-11-03"), kandang=True)

def test_memo_tidak_menyajikan_hasil_frame_lama_untuk_frame_baru(df):
    # Tes ini yang menjaga tes kebocoran tetap jujur: memo yang mengabaikan kuncinya
    # akan membuat tes pemotongan frame lulus tanpa membuktikan apa pun.
    sebelum = pd.Timestamp("2023-08-12")
    fitur_tim(df, "Luton", pd.Timestamp("2026-11-03"), kandang=True)  # isi slot memo dengan frame penuh
    terpotong = df[df.tanggal < sebelum].copy()  # tak memuat Luton sama sekali
    with pytest.raises(ValueError, match="Luton"):
        fitur_tim(terpotong, "Luton", sebelum, kandang=True)
