"""Identitas klub: warna aksen, singkatan tiga huruf, dan logo."""
from pathlib import Path

NETRAL = "#65736C"

# Warna utama kostum. Klub yang warna utamanya putih/pucat (Tottenham, Fulham, Swansea,
# Derby, Leeds) memakai warna kedua (navy/hitam/biru) supaya
# aksen tetap terbaca di latar #F4F6F2.
WARNA = {
    "Arsenal": "#EF0107",
    "Aston Villa": "#7A003C",
    "Birmingham": "#0B3FA8",
    "Blackburn": "#2F6DB5",
    "Blackpool": "#E8731A",
    "Bolton": "#1B2A5C",
    "Bournemouth": "#8F1A2C",  # merah tua; #C8102E milik Liverpool
    "Bradford": "#8C1D40",
    "Brentford": "#E30613",
    "Brighton": "#0057B8",
    "Burnley": "#6C1D45",
    "Cardiff": "#0070B5",
    "Charlton": "#D4021D",
    "Chelsea": "#034694",
    "Coventry": "#59B3E6",
    "Crystal Palace": "#1B458F",
    "Derby": "#1A1A1A",  # putih -> hitam
    "Everton": "#003399",
    "Fulham": "#1A1A1A",  # putih -> hitam
    "Huddersfield": "#0E63AD",
    "Hull": "#F5A12D",
    "Ipswich": "#3A64A3",
    "Leeds": "#1D428A",  # putih -> biru tua
    "Leicester": "#003090",
    "Liverpool": "#C8102E",
    "Luton": "#F78F1E",
    "Man City": "#6CABDD",
    "Man United": "#DA291C",
    "Middlesbrough": "#E21A23",
    "Newcastle": "#241F20",
    "Norwich": "#00A650",
    "Nott'm Forest": "#DD0000",
    "Portsmouth": "#001C58",
    "QPR": "#1D5BA4",
    "Reading": "#004494",
    "Sheffield United": "#EE2737",
    "Southampton": "#D71920",
    "Stoke": "#E03A3E",
    "Sunderland": "#EB172B",
    "Swansea": "#1A1A1A",  # putih -> hitam
    "Tottenham": "#132257",  # putih -> navy
    "Watford": "#FBEE23",
    "West Brom": "#122F67",
    "West Ham": "#7A263A",
    "Wigan": "#1F5FA8",
    "Wolves": "#FDB913",
}

# Kode eksplisit untuk semua klub yang akan bertabrakan bila diturunkan dari
# tiga huruf pertama (BLA, MAN, WES), plus yang kodenya berbeda dari konvensi.
SINGKATAN = {
    "Blackburn": "BLB",
    "Blackpool": "BLP",
    "Man City": "MCI",
    "Man United": "MUN",
    "West Brom": "WBA",
    "West Ham": "WHU",
    "Nott'm Forest": "NFO",
}


# Nama di dataset -> berkas di data/logo_pl (manifest memakai nama lengkap klub).
# Tabel eksplisit; tidak ada pencocokan awalan atau potongan nama.
LOGO = {
    "Arsenal": "arsenal.png",
    "Aston Villa": "aston_villa.png",
    "Bournemouth": "afc_bournemouth.png",
    "Brentford": "brentford.png",
    "Brighton": "brighton_hove_albion.png",
    "Burnley": "burnley.png",
    "Chelsea": "chelsea.png",
    "Coventry": "coventry_city.png",
    "Crystal Palace": "crystal_palace.png",
    "Everton": "everton.png",
    "Fulham": "fulham.png",
    "Hull": "hull_city.png",
    "Ipswich": "ipswich_town.png",
    "Leeds": "leeds_united.png",
    "Leicester": "leicester_city.png",
    "Liverpool": "liverpool.png",
    "Luton": "luton_town.png",
    "Man City": "manchester_city.png",
    "Man United": "manchester_united.png",
    "Newcastle": "newcastle_united.png",
    "Norwich": "norwich_city.png",
    "Nott'm Forest": "nottingham_forest.png",
    "Sheffield United": "sheffield_united.png",
    "Southampton": "southampton.png",
    "Sunderland": "sunderland.png",
    "Tottenham": "tottenham_hotspur.png",
    "Watford": "watford.png",
    "West Ham": "west_ham_united.png",
    "Wolves": "wolverhampton_wanderers.png",
}
FOLDER_LOGO = Path(__file__).resolve().parent.parent / "data" / "logo_pl"

# Klub yang tidak main di musim berjalan; logonya disimpan terpisah di data/logo.
LOGO_LAMA = {
    "Birmingham": "BirminghamCity_ClubLogo.png",
    "Blackburn": "BlackburnRovers_ClubLogo.png",
    "Blackpool": "Blackpool_ClubLogo.png",
    "Bolton": "BoltonWanderers_ClubLogo.png",
    "Bradford": "BradfordCity_ClubLogo.png",
    "Cardiff": "CardiffCity_ClubLogo.png",
    "Charlton": "CharltonAthletic_ClubLogo.png",
    "Derby": "DerbyCounty_ClubLogo.png",
    "Huddersfield": "HuddersfieldTown_ClubLogo.png",
    "Middlesbrough": "Middlesbrough_ClubLogo.png",
    "Portsmouth": "Portsmouth_ClubLogo.png",
    "QPR": "QueensParkRangers_ClubLogo.png",
    "Reading": "Reading_ClubLogo.png",
    "Stoke": "StokeCity_ClubLogo.png",
    "Swansea": "SwanseaCity_ClubLogo.png",
    "West Brom": "WestBromwichAlbion_ClubLogo.png",
    "Wigan": "WiganAthletic_ClubLogo.png",
}
FOLDER_LOGO_LAMA = Path(__file__).resolve().parent.parent / "data" / "logo"


def logo_klub(nama: str) -> Path | None:
    """Berkas logo klub, atau None bila tidak ada. Pemanggil memakai singkatan() sebagai cadangan."""
    if nama in LOGO:
        jalur = FOLDER_LOGO / LOGO[nama]
    elif nama in LOGO_LAMA:
        jalur = FOLDER_LOGO_LAMA / LOGO_LAMA[nama]
    else:
        return None
    return jalur if jalur.is_file() else None


def warna_klub(nama: str) -> str:
    return WARNA.get(nama, NETRAL)


def singkatan(nama: str) -> str:
    return SINGKATAN.get(nama, nama[:3].upper())
