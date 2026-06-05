import requests
from bs4 import BeautifulSoup
import re
import time
import uuid
import json
from datetime import datetime

iller_map = {
    "adana": "Adana",
    "adiyaman": "Adıyaman",
    "afyonkarahisar": "Afyonkarahisar",
    "agri": "Ağrı",
    "amasya": "Amasya",
    "ankara": "Ankara",
    "antalya": "Antalya",
    "artvin": "Artvin",
    "aydin": "Aydın",
    "balikesir": "Balıkesir",
    "bilecik": "Bilecik",
    "bingol": "Bingöl",
    "bitlis": "Bitlis",
    "bolu": "Bolu",
    "burdur": "Burdur",
    "bursa": "Bursa",         # <-- AKTİF: TEST İLİ
    "canakkale": "Çanakkale",
    "cankiri": "Çankırı",
    "corum": "Çorum",
    "denizli": "Denizli",
    "diyarbakir": "Diyarbakır",
    "edirne": "Edirne",
    "elazig": "Elazığ",
    "erzincan": "Erzincan",
    "erzurum": "Erzurum",
    "eskisehir": "Eskişehir",
    "gaziantep": "Gaziantep",
    "giresun": "Giresun",
    "gumushane": "Gümüşhane",
    "hakkari": "Hakkari",
    "hatay": "Hatay",
    "isparta": "Isparta",
    "mersin": "Mersin",
    "istanbul": "İstanbul",
    "izmir": "İzmir",
    "kars": "Kars",
    "kastamonu": "Kastamonu",
    "kayseri": "Kayseri",
    "kirklareli": "Kırklareli",
    "kirsehir": "Kırşehir",
    "kocaeli": "Kocaeli",
    "konya": "Konya",
    "kutahya": "Kütahya",
    "malatya": "Malatya",
    "manisa": "Manisa",
    "kahramanmaras": "Kahramanmaraş",
    "mardin": "Mardin",
    "mugla": "Muğla",
    "mus": "Muş",
    "nevsehir": "Nevşehir",
    "nigde": "Niğde",
    "ordu": "Ordu",
    "rize": "Rize",
    "sakarya": "Sakarya",
    "samsun": "Samsun",
    "siirt": "Siirt",
    "sinop": "Sinop",
    "sivas": "Sivas",
    "tekirdag": "Tekirdağ",
    "tokat": "Tokat",
    "trabzon": "Trabzon",
    "tunceli": "Tunceli",
    "sanliurfa": "Şanlıurfa",
    "usak": "Uşak",
    "van": "Van",
    "yozgat": "Yozgat",
    "zonguldak": "Zonguldak",
    "aksaray": "Aksaray",
    "bayburt": "Bayburt",
    "karaman": "Karaman",
    "kirikkale": "Kırıkkale",
    "batman": "Batman",
    "sirnak": "Şırnak",
    "bartin": "Bartın",
    "ardahan": "Ardahan",
    "igdir": "Iğdır",
    "yalova": "Yalova",
    "karabuk": "Karabük",
    "kilis": "Kilis",
    "osmaniye": "Osmaniye",
    "duzce": "Düzce",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

def guvenli_sql(metin, max_uzunluk=None):
    if not metin:
        return ""
    temiz = str(metin).replace("\\", "\\\\").replace("'", "''").strip()
    temiz = re.sub(r'\s+', ' ', temiz)
    if max_uzunluk:
        return temiz[:max_uzunluk]
    return temiz

# -----------------------------------------------------------------
# Mobil uygulama haritası için Enlem (X) ve Boylam (Y) koordinat bulucu.
# OpenStreetMap Nominatim API kullanılır.
# -----------------------------------------------------------------
def koordinat_bul(eczane_adi, ilce, sehir):
    url = "https://nominatim.openstreetmap.org/search"
    headers_osm = {'User-Agent': 'MedoraApp-BTU-Project'}

    # 1. Aşama: Eczane adıyla tam konum araması
    arama_metni = f"{eczane_adi}, {ilce}, {sehir}"
    params = {'q': arama_metni, 'format': 'json', 'limit': 1}

    try:
        time.sleep(1.2)  # Nominatim rate-limit: max 1 istek/saniye
        res = requests.get(url, params=params, headers=headers_osm)
        data = res.json()
        if data:
            lat = data[0]['lat']
            lon = data[0]['lon']
            print(f"    [KOORDİNAT] {eczane_adi} → {lat}, {lon}")
            return f"'{lat}'", f"'{lon}'"

        # 2. Aşama: İlçe merkezine sabitle
        time.sleep(1.2)
        params['q'] = f"{ilce}, {sehir}"
        res = requests.get(url, params=params, headers=headers_osm)
        data = res.json()
        if data:
            lat = data[0]['lat']
            lon = data[0]['lon']
            print(f"    [KOORDİNAT-İLÇE] {eczane_adi} için ilçe merkezi kullanıldı → {lat}, {lon}")
            return f"'{lat}'", f"'{lon}'"

    except Exception as e:
        print(f"    [KOORDİNAT HATA] {eczane_adi}: {e}")

    return "NULL", "NULL"

bugunun_tarihi = datetime.now().strftime('%Y-%m-%d')
nobetci_listesi = []  # HTML harita için koordinat listesini biriktir

# -----------------------------------------------------------------
# SQL dosyası üretimi
# -----------------------------------------------------------------
with open("nobetci_eczaneler.sql", "w", encoding="utf-8") as sql_dosyasi:

    sql_dosyasi.write("-- MEDORA Nöbetçi Eczaneler Veritabanı Kayıtları (Harita Entegrasyonlu)\n")
    sql_dosyasi.write(f"-- Tarih: {bugunun_tarihi}\n")
    sql_dosyasi.write("CREATE DATABASE IF NOT EXISTS medora_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n")
    sql_dosyasi.write("USE medora_db;\n\n")

    sql_dosyasi.write("CREATE TABLE IF NOT EXISTS nobetci_eczaneler (\n")
    sql_dosyasi.write("    nobet_id CHAR(36) PRIMARY KEY,\n")
    sql_dosyasi.write("    ad VARCHAR(200),\n")
    sql_dosyasi.write("    tel_no VARCHAR(30),\n")
    sql_dosyasi.write("    adres TEXT,\n")
    sql_dosyasi.write("    il VARCHAR(100),\n")
    sql_dosyasi.write("    ilce VARCHAR(100),\n")
    sql_dosyasi.write("    nobet_bitis_saati TIME,\n")
    sql_dosyasi.write("    tarih DATE,\n")
    sql_dosyasi.write("    enlem VARCHAR(50),   -- X ekseni (Latitude)\n")
    sql_dosyasi.write("    boylam VARCHAR(50)   -- Y ekseni (Longitude)\n")
    sql_dosyasi.write(");\n\n")

    for url_il, gercek_il in iller_map.items():
        print(f"\n{'='*60}")
        print(f"  {gercek_il} ili nöbetçi eczaneleri taranıyor ({bugunun_tarihi})...")
        print(f"{'='*60}")
        url = f"https://www.eczaneler.gen.tr/nobetci-{url_il}"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")

            tablolar = soup.find_all("table")

            if not tablolar:
                print(f"  UYARI: {gercek_il} için tablo bulunamadı.")
                continue

            kayit_sayisi = 0
            for indeks, tablo in enumerate(tablolar):
                if indeks != 1:
                    continue

                satirlar = tablo.find_all("tr")
                for satir in satirlar:
                    satir_metni = satir.get_text(separator=" | ", strip=True)

                    telefonlar = re.findall(r"0\s*\(\d{3}\)\s*\d{3}-\d{2}-\d{2}", satir_metni)

                    if not telefonlar or len(telefonlar) > 3:
                        continue

                    telefon_metni = guvenli_sql(" - ".join(telefonlar), 30)
                    parcalar = [p.strip() for p in satir_metni.split(" | ") if p.strip()]
                    eczane_adi_ham = parcalar[0]
                    eczane_adi = guvenli_sql(eczane_adi_ham, 200)

                    adres_parcalari = []
                    telefonlar_listesi = []
                    telefon_basladi = False

                    for p in parcalar[1:]:
                        if re.search(r"0\s*\(\d{3}\)\s*\d{3}-\d{2}-\d{2}", p):
                            telefon_basladi = True
                            telefonlar = re.findall(r"0\s*\(\d{3}\)\s*\d{3}-\d{2}-\d{2}", p)
                            telefonlar_listesi.extend(telefonlar)
                        else:
                            if telefon_basladi:
                                break
                            else:
                                adres_parcalari.append(p)

                    if not telefonlar_listesi:
                        continue

                    telefon_metni = guvenli_sql(" - ".join(telefonlar_listesi), 30)
                    ham_adres = " ".join(adres_parcalari)

                    not_bul = re.search(r"\(([^)]*(nöbetçi|kadar|arası|açık)[^)]*)\)", ham_adres, re.IGNORECASE)
                    bitis_saati_sql = "NULL"
                    bitis_saati_goster = ""
                    temiz_adres = ham_adres

                    if not_bul:
                        ozel_not = not_bul.group(1).strip()
                        temiz_adres = ham_adres.replace(f"({not_bul.group(1)})", "").strip()
                        saatler = re.findall(r"\d{2}:\d{2}", ozel_not)
                        if saatler:
                            bitis_saati_sql = f"'{saatler[-1]}:00'"
                            bitis_saati_goster = saatler[-1]

                    temiz_adres_sql = guvenli_sql(temiz_adres)

                    ilce = ""
                    match = re.search(r"/\s*" + re.escape(gercek_il), temiz_adres, re.IGNORECASE)
                    if match:
                        oncesi = temiz_adres[:match.start()].strip()
                        oncesi = oncesi.rstrip(",.-")
                        kelimeler = oncesi.split()
                        if kelimeler:
                            ilce = kelimeler[-1]
                            if ilce.lower() == "merkez":
                                ilce = f"{gercek_il} Merkez"

                    ilce_sql = guvenli_sql(ilce, 100)
                    sehir_sql = guvenli_sql(gercek_il, 100)
                    nobet_id = str(uuid.uuid4())

                    # Harita koordinatlarını çek
                    enlem_sql, boylam_sql = koordinat_bul(eczane_adi_ham, ilce, gercek_il)

                    insert_sorgusu = (
                        f"INSERT INTO nobetci_eczaneler "
                        f"(nobet_id, ad, tel_no, adres, il, ilce, nobet_bitis_saati, tarih, enlem, boylam) VALUES "
                        f"('{nobet_id}', '{eczane_adi}', '{telefon_metni}', '{temiz_adres_sql}', "
                        f"'{sehir_sql}', '{ilce_sql}', {bitis_saati_sql}, '{bugunun_tarihi}', "
                        f"{enlem_sql}, {boylam_sql});\n"
                    )
                    sql_dosyasi.write(insert_sorgusu)
                    kayit_sayisi += 1

                    # HTML harita için listeye ekle
                    if enlem_sql != "NULL" and boylam_sql != "NULL":
                        nobetci_listesi.append({
                            "ad": eczane_adi_ham,
                            "adres": temiz_adres,
                            "telefon": " - ".join(telefonlar_listesi),
                            "sehir": gercek_il,
                            "ilce": ilce,
                            "bitis": bitis_saati_goster,
                            "tarih": bugunun_tarihi,
                            "enlem": enlem_sql.strip("'"),
                            "boylam": boylam_sql.strip("'")
                        })

            print(f"  TAMAM: {kayit_sayisi} nöbetçi eczane kaydedildi.")
            time.sleep(1)

        except Exception as e:
            print(f"  HATA: {gercek_il} verileri çekilirken: {e}")

print("\n" + "="*60)
print("SQL dosyası tamamlandı: nobetci_eczaneler.sql")
print(f"Toplam koordinatlı nöbetçi eczane: {len(nobetci_listesi)}")
print("="*60)
