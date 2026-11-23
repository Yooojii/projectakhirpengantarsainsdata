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


# ------------------------------------------------- regresi perbaikan Overview

def _df():
    return muat_pertandingan()


def test_klub_tanpa_laga_di_rentang_tidak_error():
    from inti.liga import klasemen, proporsi_hasil, radar
    df = _df()
    sub = df[df["musim"] == "2026/27"]
    assert klasemen(sub[sub["tim_kandang"] == "Bradford"]).empty
    assert [b["nilai"] for b in proporsi_hasil(sub, None, "Bradford")] == [0.0, 0.0, 0.0]
    assert radar(sub, None, "Bradford") == []


def test_tren_klub_hanya_menghitung_sisi_klub():
    from inti.liga import laga_klub, tren_musim
    df = _df()
    sub = df[df["musim"] == "2023/24"]
    liga = tren_musim(laga_klub(sub, "Arsenal"))
    klub = tren_musim(laga_klub(sub, "Arsenal"), "Arsenal")
    # 91 gol Arsenal dari 38 laga, bukan gol kedua tim
    assert klub.loc[0, "gol"] == round(91 / 38, 3)
    assert klub.loc[0, "gol"] < liga.loc[0, "gol"]
    kandang = sub[sub["tim_kandang"] == "Arsenal"]
    assert klub.loc[0, "kandang"] == round(100 * (kandang["hasil"] == "H").mean(), 2)


def test_radar_liga_memakai_rata_rata_semua_klub():
    from inti.liga import radar
    seri = radar(_df(), "2024/25")
    assert [s["nama"] for s in seri] == ["Rata-rata liga"]
    assert all(0 <= v <= 1 for v in seri[0]["nilai"])


def test_rentang_musim_minimal_dua_musim():
    from halaman.overview import rentang_minimal
    musim = ["2023/24", "2024/25", "2025/26", "2026/27"]
    assert rentang_minimal(("2023/24", "2025/26"), None, musim) == ("2023/24", "2025/26")
    # ujung awal digeser ke ujung akhir di tepi kanan: awal mundur satu musim
    assert rentang_minimal(("2026/27", "2026/27"), ("2023/24", "2026/27"), musim) == ("2025/26", "2026/27")
    # ujung akhir digeser ke ujung awal: akhir maju satu musim
    assert rentang_minimal(("2024/25", "2024/25"), ("2024/25", "2026/27"), musim) == ("2024/25", "2025/26")
    # mentok di tepi kiri
    assert rentang_minimal(("2023/24", "2023/24"), ("2024/25", "2026/27"), musim) == ("2023/24", "2024/25")
    assert rentang_minimal(None, None, musim) == ("2023/24", "2026/27")


def test_pemberitahuan_klub_yang_tidak_main_di_rentang():
    from halaman.overview import _pemberitahuan_absen
    df = _df()
    sub = df[df["musim"].isin(["2025/26", "2026/27"])]
    teks = _pemberitahuan_absen(df, sub, "Bradford")
    assert "Bradford tidak main di rentang 2025/26 sampai 2026/27" in teks
    assert "2000/01" in teks
    assert _pemberitahuan_absen(df, sub, "Arsenal") == ""


def test_donat_menulis_persen_menang_bukan_irisan_terbesar():
    from gaya.panel import donat
    svg = donat([{"label": "Menang", "nilai": 13.2}, {"label": "Seri", "nilai": 28.9},
                 {"label": "Kalah", "nilai": 57.9}], "#8C1D40")
    assert ">13%</text>" in svg and ">58%</text>" not in svg


def test_kelengkapan_memakai_jumlah_laga_sebenarnya():
    df = _df()
    t = tabel_kelengkapan(df).set_index("kelompok")
    assert f"{len(df):,}".replace(",", ".") in t.loc["statistik_dasar", "alasan"]
