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
        for a in p.atribut:  # termasuk refleks milik kiper
            assert 1 <= p.atribut[a] <= 99
    assert any("refleks" in p.atribut for p in bangkitkan_skuad(df, "Man City", TGL))

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

def _rata(df, klub, atribut, posisi=None):
    s = [p for p in bangkitkan_skuad(df, klub, TGL) if p.inti and (posisi is None or p.posisi == posisi)]
    return sum(p.atribut[atribut] for p in s) / len(s)

def test_arah_atribut_terbalik_mengikuti_statistik(df):
    # antisipasi, ketenangan, refleks: makin sedikit kebobolan/kartu, makin tinggi
    from inti.fitur import fitur_tim
    f = {k: fitur_tim(df, k, TGL, True) for k in df[df["musim"] == "2026/27"]["tim_kandang"].unique()}
    sedikit_bobol = min(f, key=lambda k: f[k]["rata_gol_kebobolan"])
    banyak_bobol = max(f, key=lambda k: f[k]["rata_gol_kebobolan"])
    sedikit_kartu = min(f, key=lambda k: f[k]["rata_kartu_kuning"])
    banyak_kartu = max(f, key=lambda k: f[k]["rata_kartu_kuning"])
    assert _rata(df, sedikit_bobol, "antisipasi") > _rata(df, banyak_bobol, "antisipasi")
    assert _rata(df, sedikit_bobol, "refleks", "KIP") > _rata(df, banyak_bobol, "refleks", "KIP")
    assert _rata(df, sedikit_kartu, "ketenangan") > _rata(df, banyak_kartu, "ketenangan")

def test_cadangan_lebih_lemah_dari_inti(df):
    s = bangkitkan_skuad(df, "Arsenal", TGL)
    rata = lambda ps: sum(sum(p.atribut[a] for a in ATRIBUT) for p in ps) / (6 * len(ps))
    assert rata([p for p in s if p.inti]) > rata([p for p in s if not p.inti])

def test_nama_unik_dan_klub_berbeda_bernama_berbeda(df):
    a = bangkitkan_skuad(df, "Arsenal", TGL)
    b = bangkitkan_skuad(df, "Everton", TGL)
    assert len({p.nama for p in a}) == 18
    assert [p.nama for p in a] != [p.nama for p in b]

def test_hasil_stabil_antar_sesi(df):
    # Nilai tetap: seed berbasis hash() akan acak per proses dan gagal di sini.
    s = bangkitkan_skuad(df, "Arsenal", TGL)
    assert [p.nama for p in s][:4] == ["Marco Pearce", "Stefan Hughes", "Jack Moreau", "Julian Nolan"]
    assert [p.atribut["refleks"] for p in s if p.posisi == "KIP"] == [86, 79]

def _dibiarkan(df):
    from inti.pemain import _tembakan_dibiarkan
    lampau = df[df["tanggal"] < TGL]
    klub = sorted(set(df[df["musim"] == "2026/27"]["tim_kandang"]))
    return klub, {k: _tembakan_dibiarkan(lampau, k) for k in klub}

def test_penguasaan_terbalik_terhadap_tembakan_dibiarkan(df):
    klub, d = _dibiarkan(df)
    sedikit, banyak = min(d, key=d.get), max(d, key=d.get)
    assert d[sedikit] < d[banyak]
    assert _rata(df, sedikit, "penguasaan") > _rata(df, banyak, "penguasaan")

def test_rebutan_terbalik_pada_tembakan_dibiarkan(df):
    # Pelanggaran ikut menentukan rebutan, jadi bandingkan dua klub dengan
    # pelanggaran paling mirip dari sepertiga atas dan bawah tembakan dibiarkan.
    from inti.fitur import fitur_tim
    klub, d = _dibiarkan(df)
    urut = sorted(klub, key=d.get)
    sepertiga = len(urut) // 3
    pel = {k: fitur_tim(df, k, TGL, True)["rata_pelanggaran"] for k in klub}
    sedikit, banyak = min(
        ((a, b) for a in urut[:sepertiga] for b in urut[-sepertiga:]),
        key=lambda ab: abs(pel[ab[0]] - pel[ab[1]]),
    )
    assert _rata(df, sedikit, "rebutan") > _rata(df, banyak, "rebutan")
