import pytest
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


def test_tren_poin_pelanggaran_pojok_liga_dan_klub():
    from inti.liga import laga_klub, tren_musim
    df = _df()
    sub = df[df["musim"] == "2023/24"]
    liga = tren_musim(sub)
    seri = (sub["hasil"] == "D").sum()
    # poin liga per tim per laga hanya ditentukan porsi seri
    assert liga.loc[0, "poin"] == round((3 * (len(sub) - seri) + 2 * seri) / (2 * len(sub)), 3)
    klub = tren_musim(laga_klub(sub, "Arsenal"), "Arsenal")
    assert klub.loc[0, "poin"] == round(89 / 38, 3)  # Arsenal 2023/24: 89 poin dari 38 laga
    assert 0 < klub.loc[0, "pelanggaran"] < 30 and 0 < klub.loc[0, "pojok"] < 15


def test_grafik_tren_memakai_warna_yang_diberikan():
    import json
    import pandas as pd
    from halaman.overview import grafik_tren
    data = pd.DataFrame({"musim": ["2024/25", "2025/26"], "tahun": ["2024", "2025"],
                         "laga": [380, 380], "pojok": [5.2, 4.7]})
    spek = json.dumps(grafik_tren(data, "pojok", "pojok", ".1f", "#B91C1C").to_dict())
    assert '"#B91C1C"' in spek and "rgba(185,28,28" in spek
    # sumbu Y grafik tren wajib mulai dari 0
    assert '"zero": true' in spek and '"zero": false' not in spek


def test_delta_pelanggaran_turun_dianggap_membaik():
    from halaman.overview import _delta_badge
    _, membaik = _delta_badge([12.0, 11.0], lebih_baik_naik=False)
    assert membaik is True
    _, membaik = _delta_badge([5.2, 4.7], lebih_baik_naik=True)
    assert membaik is False


def test_radar_menampilkan_angka_asli_saat_disorot():
    from gaya.panel import radar as gambar_radar
    from inti.liga import SUMBU_RADAR, radar
    seri = radar(_df(), "2023/24", "Arsenal")
    assert [round(x, 2) for x in seri[0]["mentah"]][2] == round(29 / 38, 2)  # kebobolan Arsenal
    svg = gambar_radar(seri, SUMBU_RADAR, "#C8102E")
    assert svg.count('class="radar-info"') == 5 and svg.count('class="radar-tip"') == 5
    assert "gol kebobolan per laga" in svg and "Premier League" in svg
    assert "0,76" in svg  # angka ditulis dengan koma desimal


def test_radar_skala_satu_sampai_lima():
    from gaya.panel import radar as gambar_radar, skor_lima
    from inti.liga import SUMBU_RADAR, radar
    assert skor_lima(0.0) == 1 and skor_lima(1.0) == 5 and skor_lima(0.5) == 3
    seri = radar(_df(), "2023/24", "Arsenal")
    svg = gambar_radar(seri, SUMBU_RADAR, "#C8102E")
    assert 'class="radar-skor"' not in svg  # skor tidak ditulis di sudut, hanya di kotak hover
    for v in seri[0]["nilai"]:
        assert f"{skor_lima(v):.1f}".replace(".", ",") in svg
    assert "/ 5" in svg and "Profil" not in svg  # judul kartu ditulis halaman, bukan SVG


def test_kandang_tandang_liga_dan_klub():
    from inti.liga import kandang_tandang
    df = _df()
    sub = df[df["musim"] == "2023/24"]
    liga = {b["label"]: b for b in kandang_tandang(sub)}
    h, d, a = ((sub["hasil"] == x).mean() for x in "HDA")
    assert round(liga["Poin per laga"]["kandang"], 6) == round(3 * h + d, 6)
    assert round(liga["Poin per laga"]["tandang"], 6) == round(3 * a + d, 6)
    klub = {b["label"]: b for b in kandang_tandang(sub, "Arsenal")}
    kandang = sub[sub["tim_kandang"] == "Arsenal"]
    assert klub["Tembakan per laga"]["kandang"] == kandang["tembakan_kandang"].mean()
    assert klub["Sepak pojok per laga"]["kandang"] == kandang["sepak_pojok_kandang"].mean()
    assert klub["Pelanggaran per laga"]["lebih_baik_naik"] is False
    assert list(klub) == ["Tembakan per laga", "Poin per laga", "Pelanggaran per laga",
                          "Sepak pojok per laga"]
    assert kandang_tandang(sub, "Bradford") == []  # tidak main di musim itu


def test_kartu_kandang_tandang_dan_tren_tanpa_menang_kandang():
    from gaya.panel import kandang_tandang as gambar
    from halaman.overview import METRIK
    from inti.liga import kandang_tandang
    html = gambar(kandang_tandang(_df()), "#157D7B")
    assert html.count('class="kt-baris"') == 4 and "Kandang" in html and "Tandang" in html
    assert "Menang Kandang" not in [m[1] for m in METRIK]


def test_radar_liga_memakai_rata_rata_semua_klub():
    from inti.liga import radar
    seri = radar(_df(), "2024/25")
    assert [s["nama"] for s in seri] == ["Premier League"]
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
