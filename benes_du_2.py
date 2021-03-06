import json, os, argparse
from pyproj import CRS, Transformer
from math import sqrt
from sys import exit

CESTA_KONTEJNERY = "kontejnery.geojson"
CESTA_ADRESY = "adresy.geojson"

wgsdojtsk = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(5514))

"""Bonus, ktery nacte soubor jako parametr za pomoci modulu Argparse."""
parser = argparse.ArgumentParser()
parser.add_argument('-a', '--adresni_body', required=False, default=None)
parser.add_argument('-k', '--kontejnery', required=False, default=None)
args = parser.parse_args()
if args.adresni_body != None:
    path_adresy = args.adresni_body
if args.kontejnery != None:
    path_kontejnery = args.kontejnery

def nacteni_souboru(nazev):
    """Nacteni souboru a validace, zda soubor existuje a ma k nemu pristup."""
    try:
        with open(nazev, "r", encoding="UTF-8") as soubor:
            return json.load(soubor)["features"]
    except FileNotFoundError: # zjistuje, zda existuje
        print(f"CHYBA: Pozadovany soubor {nazev} neexistuje. Program skonci.")
        exit()
    except PermissionError: # zjistuje pristup k souboru
        print(f"CHYBA: Nemam pristup k {nazev}.Program skonci.")
        exit()
    except ValueError as e: # validuje i pokud se jedna o validni JSON
        print(f"CHYBA: Soubor {nazev} neni validni. Program skonci.\n", e)
        exit()
        
def cteni_kontejneru(misto):
    """Cte informace z kontejnery.json potrebne pro praci. Pokud PRISTUP neni 
    volne, tak nastavi souradnice None."""
    ulice = misto["properties"]["STATIONNAME"]
    souradnice = misto["geometry"]["coordinates"]
    pristup = misto["properties"]["PRISTUP"]

    if pristup=="volně": # selekce pouze volne stojicich kontejneru
        return ulice, souradnice
    return ulice, None

def cteni_adresy(misto):
    """Cte ulice a cisla domu, vysledek spoji, dale cte souradnice danych mist."""
    ulice = misto["properties"]["addr:street"] + " " + misto["properties"]["addr:housenumber"]
    souradnice_sirka = misto["geometry"]["coordinates"][1]
    souradnice_delka = misto["geometry"]["coordinates"][0]

    return ulice, wgsdojtsk.transform(souradnice_sirka, souradnice_delka)

def nacteni_dat(data, jeToKontejner=True):
    """Deli cteni kontejneru a adres, uklada je do datove struktury s klicem reprezentujicim 
    ulici a hodnotu reprezentujici souradnice, souradnice mohou byt none v pripade, ze k nim 
    neni volny pristup. Spocita vyrazene adresy a kontejnery, u kterych se nachazi potrebna 
    data, na konci napise kolik je vyrazenych zaznamu"""
    nacteni = {}
    pocet_neplatnych = 0

    for misto in data:
        try:
            if jeToKontejner:
                ulice, souradnice = cteni_kontejneru(misto)
            else:
                ulice, souradnice = cteni_adresy(misto)
            
            nacteni[ulice] = souradnice
        except KeyError:
            pocet_neplatnych+=1

    nazev = "kontejneru"
    if jeToKontejner==False:
        nazev = "adres"

    if pocet_neplatnych > 0:
        print(f"POZOR: vyradil jsem {pocet_neplatnych} {nazev}, protoze neobsahovala potrebna data.")

    if len(nacteni)==0:
        print(f"CHYBA: nemam k dispozici dostatecny pocet dat pro vypocet (u {nazev}).")
        exit()

    return (nacteni)
    
def pythagoras(s1, s2):
    """Vypocet vzdalenosti bodu pomoci Pythagorovy vety."""
    return sqrt((s1[0] - s2[0])**2 + (s1[1] - s2[1])**2)

def hledani_min_vzdalenosti(kontejnery, adresy):
    """Hleda minimalni vzdalenost od kontejneru."""
    vzdalenosti = {}

    for (adresa_ulice, adresa_souradnice) in adresy.items():

        min_vzd = -1
        prvni = True

        for kontejnery_ulice, kontejnery_souradnice in kontejnery.items():
            if kontejnery_souradnice==None and kontejnery_ulice==adresa_ulice:
                min_vzd = 0
                break
            if kontejnery_souradnice==None:
                continue
            
            vzdalenost = pythagoras(adresa_souradnice, kontejnery_souradnice)
            if prvni or vzdalenost < min_vzd:
                min_vzd = vzdalenost
                prvni = False

        if min_vzd > 10000: # osetreni, ze vzdalenost je mensi nez 10 km
            print(" CHYBA: Kontejner je dale nez 10 km.")
            exit()

        vzdalenosti[adresa_ulice] = min_vzd

    return vzdalenosti

def median(vzdalenosti):
    """Vypocet medianu"""
    sez_vzdalenosti = list(vzdalenosti.values())
    sez_vzdalenosti.sort()
    p = (len(sez_vzdalenosti) - 1) // 2

    # kdyz vyjde zbytek po vypoctu 0, program vypise false
    # kdyz vyjde zbytek po vypoctu 1, program vypise true
    if len(sez_vzdalenosti) % 2:
        return sez_vzdalenosti[p]

    return (sez_vzdalenosti[p] + sez_vzdalenosti[p + 1]) / 2

os.path.dirname(os.path.abspath(__file__))

data_kontejnery = nacteni_souboru(CESTA_KONTEJNERY)
data_adresy = nacteni_souboru(CESTA_ADRESY)

nacteni_kontejnery = nacteni_dat(data_kontejnery)

nacteni_adresy = nacteni_dat(data_adresy, False)

vzdalenosti = hledani_min_vzdalenosti(nacteni_kontejnery, nacteni_adresy)

prumer = sum(vzdalenosti.values()) / len(vzdalenosti)

median = median(vzdalenosti)

maximum = max(vzdalenosti.values())

for (adresa, vzdalenost) in vzdalenosti.items():
    if vzdalenost == maximum:
        nejvzdalenejsi = adresa

# vypsani vysledku v terminalu

print()
print(f"Nacteno adresnich bodu: {len(nacteni_adresy)}")
print(f"Nacteno kontejneru na trideny odpad: {len(nacteni_kontejnery)}")
print()
print(f"Prumerna vzdalenost adresniho bodu ke kontejneru: "f"{prumer:.0f}"" metru")
print(f"Median vzdalenosti ke kontejneru: {median:.0f} metru")
print()
print(f"Nejdale je ke kontejneru je z adresniho bodu '{nejvzdalenejsi}', konkretne {maximum:.0f} metru")