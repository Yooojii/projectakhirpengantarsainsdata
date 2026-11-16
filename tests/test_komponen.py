import re
import colorsys
from pathlib import Path

import altair as alt
import pandas as pd
import pytest

from gaya.komponen import (
    BACA_CSS,
    bar_atribut,
    grafik_dasar,
    papan_skor,
    pasang_tema,
    warna_aksen,
)
from inti.klub import NETRAL, WARNA, warna_klub

LATAR = "#F4F6F2"
GARIS = "#CFD6CC"


def _luminans(heks: str) -> float:
    kanal = []
    for i in (1, 3, 5):
        c = int(heks[i:i + 2], 16) / 255
        kanal.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * kanal[0] + 0.7152 * kanal[1] + 0.0722 * kanal[2]


def kontras(a: str, b: str = LATAR) -> float:
    la, lb = sorted((_luminans(a), _luminans(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _hue(heks: str) -> float:
    r, g, b = (int(heks[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)[0]


def _cari(obj, kunci):
    hasil = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == kunci:
                hasil.append(v)
            hasil.extend(_cari(v, kunci))
    elif isinstance(obj, list):
        for v in obj:
            hasil.extend(_cari(v, kunci))
    return hasil


# ---------------------------------------------------------------- warna_aksen

def test_kontras_dihitung_benar():
    assert kontras("#000000", "#FFFFFF") == pytest.approx(21.0)
    assert kontras("#FFFFFF", "#FFFFFF") == pytest.approx(1.0)


@pytest.mark.parametrize("klub", sorted(WARNA))
def test_aksen_setiap_klub_lolos_kontras_45(klub):
    assert kontras(warna_aksen(warna_klub(klub))) >= 4.5


def test_warna_yang_sudah_lolos_tidak_diubah():
    lolos = [h for h in WARNA.values() if kontras(h) >= 4.5]
    assert lolos, "harus ada klub yang sudah lolos"
    for h in lolos:
        assert warna_aksen(h) == h


def test_warna_pucat_digelapkan_dengan_rona_tetap():
    for klub in ["Watford", "Hull", "Man City", "Wolves", "Norwich"]:
        asli = warna_klub(klub)
        aksen = warna_aksen(asli)
        assert aksen != asli
        assert abs(_hue(aksen) - _hue(asli)) < 0.02
        assert _luminans(aksen) < _luminans(asli)


def test_aksen_idempoten_dan_netral_lolos():
    for h in WARNA.values():
        assert warna_aksen(warna_aksen(h)) == warna_aksen(h)
    assert kontras(warna_aksen(NETRAL)) >= 4.5


# ------------------------------------------------------------------------ css

def test_css_memuat_token_warna_dan_tanpa_bayangan():
    css = BACA_CSS()
    for warna in ["#F4F6F2", "#0E1F18", "#6B7A72", "#CFD6CC", "#FFFFFF", "#E0A800", "#C8102E"]:
        assert warna in css
    for nilai in re.findall(r"box-shadow\s*:\s*([^;}]+)", css):
        assert nilai.replace("!important", "").strip() == "none"
    assert "text-shadow" not in css and "drop-shadow" not in css
    assert "IBM Plex Sans Condensed" in css and "IBM Plex Sans" in css
    assert "fonts.googleapis.com" in css
    assert "tabular-nums" in css


def test_css_token_di_root_dan_aksen_dapat_ditulis_ulang():
    css = BACA_CSS()
    root = re.search(r":root\s*\{([^}]*)\}", css).group(1)
    for token in ["--latar", "--teks", "--aksen", "--garis"]:
        assert token in root


def test_css_tanpa_hal_yang_dilarang():
    css = BACA_CSS().lower()
    assert "gradient" not in css
    assert "uppercase" not in css
    assert ":hover" not in css
    assert "#0b0b0b" not in css and not re.search(r"#111(?![0-9a-f])", css)
    assert not re.search("[\U0001F300-\U0001FAFF←-⇿☀-➿]", css)
    assert "prefers-reduced-motion" in css
    assert "dark" not in css


def test_css_radius_empat_piksel_dan_jarak_kelipatan_delapan():
    css = BACA_CSS()
    for r in re.findall(r"border-radius\s*:\s*([^;}]+)", css):
        assert r.strip() in {"4px", "50%", "0"}
    for ukuran in re.findall(r"(?:margin|padding|gap)[a-z-]*\s*:\s*([^;}]+)", css):
        for angka in re.findall(r"(\d+)px", ukuran):
            assert int(angka) % 8 == 0 or int(angka) == 4, ukuran


def test_css_hanya_satu_gerakan():
    css = BACA_CSS()
    assert css.count("@keyframes") == 1
    assert "transition" not in css


def test_tema_dikunci_terang():
    cfg = Path(__file__).resolve().parent.parent / ".streamlit" / "config.toml"
    assert 'base = "light"' in cfg.read_text(encoding="utf-8")


def test_pasang_tema_menyuntik_css_dengan_aksen_terjamin(monkeypatch):
    kiriman = []
    import gaya.komponen as k
    monkeypatch.setattr(k.st, "markdown", lambda s, **kw: kiriman.append((s, kw)))
    pasang_tema("#FBEE23")  # kuning Watford: harus digelapkan
    assert len(kiriman) == 1
    teks, kw = kiriman[0]
    assert kw.get("unsafe_allow_html") is True
    ekor = teks[teks.rfind(":root"):]
    aksen = re.search(r"--aksen\s*:\s*(#[0-9A-Fa-f]{6})", ekor).group(1)
    assert aksen.upper() == warna_aksen("#FBEE23").upper()
    assert kontras(aksen) >= 4.5


# ----------------------------------------------------------------- papan_skor

PELUANG = {"menang": 0.54, "seri": 0.24, "kalah": 0.22}


def test_papan_skor_memuat_kedua_klub_dan_tiga_peluang():
    h = papan_skor("Arsenal", "Tottenham", (2, 1), PELUANG, "#DB0007")
    assert "Arsenal" in h and "Tottenham" in h
    assert "54" in h and "24" in h and "22" in h
    assert "→" not in h


def test_papan_skor_kandang_sebelum_skor_sebelum_tamu():
    h = papan_skor("Arsenal", "Tottenham", (2, 1), PELUANG, "#DB0007")
    assert h.index("Arsenal") < h.index(">2<") < h.index(">1<") < h.index("Tottenham")


def test_papan_skor_tanpa_gambar_dan_nama_di_escape():
    h = papan_skor("A<b>", "C&D", (0, 0), PELUANG, "#DB0007")
    assert "<img" not in h.lower() and "<svg" not in h.lower()
    assert "<b>" not in h and "&lt;b&gt;" in h and "C&amp;D" in h


# ---------------------------------------------------------------- bar_atribut

def _terisi(h):
    return h.count("terisi")


def test_bar_atribut_delapan_ruas_terisi_proporsional():
    assert bar_atribut(99, "#DB0007").count("ruas") == 8
    assert _terisi(bar_atribut(99, "#DB0007")) == 8
    assert _terisi(bar_atribut(50, "#DB0007")) == 4
    assert _terisi(bar_atribut(0, "#DB0007")) == 0
    assert _terisi(bar_atribut(99, "#DB0007")) > _terisi(bar_atribut(20, "#DB0007"))


def test_bar_atribut_angka_di_samping_dan_nilai_di_luar_batas():
    assert ">80<" in bar_atribut(80, "#DB0007")
    assert _terisi(bar_atribut(150, "#DB0007")) == 8
    assert _terisi(bar_atribut(-5, "#DB0007")) == 0


def test_bar_atribut_lawan_abu_dan_klub_saya_aksen():
    assert "#6B7A72" in bar_atribut(80, None)
    assert "#DB0007" not in bar_atribut(80, None)
    assert "#DB0007" in bar_atribut(80, "#DB0007")


def test_bar_atribut_aksen_pucat_digelapkan():
    h = bar_atribut(80, "#FBEE23")
    assert "#FBEE23" not in h.upper()
    assert warna_aksen("#FBEE23") in h


# ---------------------------------------------------------------- grafik_dasar

@pytest.fixture
def data():
    baris = []
    for klub, dasar in [("Arsenal", 1.8), ("Chelsea", 1.9), ("Everton", 1.3)]:
        for i, m in enumerate(range(2015, 2020)):
            baris.append({"musim": m, "gol_per_laga": dasar + 0.05 * i, "klub": klub})
    return pd.DataFrame(baris)


def _skala(spec):
    return [v for v in _cari(spec, "scale") if isinstance(v, dict) and "range" in v][0]


def test_grafik_dasar_judul_dari_pemanggil_dan_tanpa_bingkai(data):
    j = "Arsenal mencetak lebih banyak gol tiap musim"
    g = grafik_dasar(data, "musim", "gol_per_laga", j, "Arsenal", "#DB0007",
                     label_x="Musim", label_y="Gol per pertandingan")
    assert isinstance(g, alt.TopLevelMixin)
    s = g.to_dict()
    judul = s["title"]["text"] if isinstance(s["title"], dict) else s["title"]
    assert judul == j
    assert s["config"]["view"]["stroke"] is None


def test_grafik_dasar_kisi_horizontal_saja_warna_garis(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", "Arsenal", "#DB0007").to_dict()
    assert s["config"]["axisX"]["grid"] is False
    assert s["config"]["axisY"]["grid"] is True
    assert s["config"]["axisY"]["gridColor"] == GARIS


def test_grafik_dasar_satu_deret_aksen_sisanya_abu(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", "Arsenal", "#DB0007").to_dict()
    sk = _skala(s)
    peta = dict(zip(sk["domain"], sk["range"]))
    assert peta["Arsenal"].upper() == "#DB0007"
    assert peta["Chelsea"] == GARIS and peta["Everton"] == GARIS
    assert None in _cari(s, "legend")


def test_grafik_dasar_aksen_pucat_digelapkan(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", "Arsenal", "#FBEE23").to_dict()
    sk = _skala(s)
    assert dict(zip(sk["domain"], sk["range"]))["Arsenal"] == warna_aksen("#FBEE23")


def test_grafik_dasar_tanpa_sorotan_semua_abu(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", None, "#DB0007").to_dict()
    assert set(_skala(s)["range"]) == {GARIS}


def test_grafik_dasar_sumbu_berkata_bukan_singkatan(data):
    s = grafik_dasar(data, "musim", "gol_per_laga", "J", "Arsenal", "#DB0007",
                     label_x="Musim", label_y="Gol per pertandingan").to_dict()
    judul = {v for v in _cari(s, "title") if isinstance(v, str)}
    assert "Gol per pertandingan" in judul and "Musim" in judul
