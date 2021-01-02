import json, os
from pyproj import CRS, Transformer
from math import sqrt
from sys import exit

CESTA_KONTEJNERY = "kontejnery.geojson"
CESTA_ADRESY = "adresy.geojson"

def ziskej_souradsys():
    """*Ziskani souradnic systemu ve formatu S-JTSK."""
    return prevod_WGS_na_SJTSK(CRS.from_epsg(4326))

def prevod_WGS_na_SJTSK(wgs):
    """*Prevod z WGS-84 na S-JTSK."""
    return Transformer.from_crs(wgs, CRS.from_epsg(5514))

def nacteni_souboru(nazev):
    """*Nacteni souboru a validace, jestli soubor existuje."""
    try:
        return open(nazev, "r", encoding="UTF-8")
    except FileNotFoundError:
        print(f"CHYBA: Pozadovany soubor {nazev} neexistuje.")
        exit()
    except PermissionError:
        print(f"CHYBA: Nemam pristup k {nazev}." )
        exit()

def cteni_jsonu_features(soubor,nazev):
    """*Prijme na vstupu soubor a jeho obsah precte jako JSON a vrati vysledek pod klicem "features". 
    Provede validaci, pokud dojde pri cteni k chybe."""
    try:
        return json.load(soubor)["features"]
    except ValueError as e: # validuje i pokud se jedna o validni JSON
        print(f"CHYBA: Soubor {nazev} neni validni.\n", e)
        exit()
        
def cteni_kontejneru(misto):
    ulice = misto["properties"]["STATIONNAME"]
    souradnice = misto["geometry"]["coordinates"]
    pristup = misto["properties"]["PRISTUP"]

    if pristup=="volně":
        return ulice, souradnice
    return None, None

def cteni_adresy(misto):
    ulice = misto["properties"]["addr:street"] + " " + misto["properties"]["addr:housenumber"]
    souradnice_sirka = misto["geometry"]["coordinates"][1]
    souradnice_delka = misto["geometry"]["coordinates"][0]

    return ulice, wgsdojtsk.transform(souradnice_sirka, souradnice_delka)

def nacteni_dat(data, jeToKontejner=True):
    nacteni = {}
    pocet_neplatnych = 0

    for misto in data:
        try:
            if jeToKontejner:
                klic, hodnota = cteni_kontejneru(misto)
            else:
                klic, hodnota = cteni_adresy(misto)
            
            if klic==None:
                continue

            nacteni[klic] = hodnota
        except KeyError:
            pocet_neplatnych+=1

    nazev = "kontejneru"
    if jeToKontejner==False:
        nazev = "adres"

    if pocet_neplatnych > 0:
        print(f"POZOR: vyradil jsem {pocet_neplatnych} {nazev}, protoze neobsahovaly potrebna data.")

    if len(nacteni)==0:
        print(f"CHYBA: nemam k dispozici dostatecny pocet dat pro vypocet (u {nazev}).")
        exit()

    return (nacteni)
    
def pythagoras(s1, s2):
    return sqrt((s1[0] - s2[0])**2 + (s1[1] - s2[1])**2)

def generovani_min_vzdalenosti(kontejnery, adresy):

    vzdalenosti = {}

    for (adresa_ulice, adresa_souradnice) in adresy.items():

        min = -1
        prvni = True

        for kontejnery_souradnice in kontejnery.values():
            vzdalenost = pythagoras(adresa_souradnice, kontejnery_souradnice)
            if prvni or vzdalenost < min:
                min = vzdalenost
                prvni = False

        if min > 10000:
            print(" CHYBA: Kontejner je dale nez 10 km.")
            exit()

        vzdalenosti[adresa_ulice] = min

    return vzdalenosti

def median(vzdalenosti):
    sez_vzdalenosti = list(vzdalenosti.values())
    sez_vzdalenosti.sort()
    p = (len(sez_vzdalenosti) - 1) // 2

    # kdyz vyjde zbytek po vypoctu 0, program vypise false
    # kdyz vyjde Zbytek po vypoctu 1, program vypise treu
    if len(sez_vzdalenosti) % 2:
        return sez_vzdalenosti[p]

    return (sez_vzdalenosti[p] + sez_vzdalenosti[p + 1]) / 2

# 
wgsdojtsk = ziskej_souradsys()

os.chdir(os.path.dirname(os.path.abspath(__file__)))

soubor_kontejnery = nacteni_souboru(CESTA_KONTEJNERY)
soubor_adresy = nacteni_souboru(CESTA_ADRESY)

data_kontejnery = cteni_jsonu_features(soubor_kontejnery, CESTA_KONTEJNERY)
data_adresy = cteni_jsonu_features(soubor_adresy, CESTA_ADRESY)

nacteni_kontejnery = nacteni_dat(data_kontejnery)

nacteni_adresy = nacteni_dat(data_adresy, False)

vzdalenosti = generovani_min_vzdalenosti(nacteni_kontejnery, nacteni_adresy)

prumer = sum(vzdalenosti.values()) / len(vzdalenosti)

median = median(vzdalenosti)

maximum = max(vzdalenosti.values())

for (adresa, vzdalenost) in vzdalenosti.items():
    if vzdalenost == maximum:
        nejvzdalenejsi = adresa

# vypsani vysledku v terminalu

print("\n")
print(f"Nacteno adresnich bodu: {len(nacteni_adresy)}")
print(f"Nacteno kontejneru na trideny odpad: {len(nacteni_kontejnery)}")

print(
    "\n"
    f"Prumerna vzdalenost adresniho bodu k verejne dostupnemu kontejneru: "f"{prumer:.0f}"" metru")

print(f"Median vzdalenosti ke kontejneru: {median:.0f} metru")
print(f"Nejdale je ke kontejneru je z adresniho bodu '{nejvzdalenejsi}' konkretne {maximum:.0f} metru")
    
