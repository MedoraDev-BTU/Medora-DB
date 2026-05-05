import requests
from bs4 import BeautifulSoup
import re
import time
import uuid

iller_map = {
    "adana": "Adana", "adiyaman": "Adıyaman", "afyonkarahisar": "Afyonkarahisar", "agri": "Ağrı", "amasya": "Amasya",
    "ankara": "Ankara", "antalya": "Antalya", "artvin": "Artvin", "aydin": "Aydın", "balikesir": "Balıkesir",
    "bilecik": "Bilecik", "bingol": "Bingöl", "bitlis": "Bitlis", "bolu": "Bolu", "burdur": "Burdur", "bursa": "Bursa",
    "canakkale": "Çanakkale", "cankiri": "Çankırı", "corum": "Çorum", "denizli": "Denizli", "diyarbakir": "Diyarbakır",
    "edirne": "Edirne", "elazig": "Elazığ", "erzincan": "Erzincan", "erzurum": "Erzurum", "eskisehir": "Eskişehir",
    "gaziantep": "Gaziantep", "giresun": "Giresun", "gumushane": "Gümüşhane", "hakkari": "Hakkari", "hatay": "Hatay",
    "isparta": "Isparta", "mersin": "Mersin", "istanbul": "İstanbul", "izmir": "İzmir", "kars": "Kars",
    "kastamonu": "Kastamonu", "kayseri": "Kayseri", "kirklareli": "Kırklareli", "kirsehir": "Kırşehir",
    "kocaeli": "Kocaeli", "konya": "Konya", "kutahya": "Kütahya", "malatya": "Malatya", "manisa": "Manisa",
    "kahramanmaras": "Kahramanmaraş", "mardin": "Mardin", "mugla": "Muğla", "mus": "Muş", "nevsehir": "Nevşehir",
    "nigde": "Niğde", "ordu": "Ordu", "rize": "Rize", "sakarya": "Sakarya", "samsun": "Samsun", "siirt": "Siirt",
    "sinop": "Sinop", "sivas": "Sivas", "tekirdag": "Tekirdağ", "tokat": "Tokat", "trabzon": "Trabzon",
    "tunceli": "Tunceli", "sanliurfa": "Şanlıurfa", "usak": "Uşak", "van": "Van", "yozgat": "Yozgat",
    "zonguldak": "Zonguldak", "aksaray": "Aksaray", "bayburt": "Bayburt", "karaman": "Karaman", "kirikkale": "Kırıkkale",
    "batman": "Batman", "sirnak": "Şırnak", "bartin": "Bartın", "ardahan": "Ardahan", "igdir": "Iğdır",
    "yalova": "Yalova", "karabuk": "Karabük", "kilis": "Kilis", "osmaniye": "Osmaniye", "duzce": "Düzce"
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

with open("tum_eczaneler.sql", "w", encoding="utf-8") as sql_dosyasi:
    
    sql_dosyasi.write("-- MEDORA Tüm Eczaneler Veritabanı Kayıtları\n")
    sql_dosyasi.write("CREATE DATABASE IF NOT EXISTS medora_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n")
    sql_dosyasi.write("USE medora_db;\n\n")
    
    sql_dosyasi.write("CREATE TABLE IF NOT EXISTS eczaneler (\n")
    sql_dosyasi.write("    eczane_id CHAR(36) PRIMARY KEY,\n")
    sql_dosyasi.write("    ad VARCHAR(150),\n")
    sql_dosyasi.write("    adres TEXT,\n")
    sql_dosyasi.write("    sehir VARCHAR(100),\n")
    sql_dosyasi.write("    ilce VARCHAR(100),\n")
    sql_dosyasi.write("    telefon VARCHAR(255)\n")
    sql_dosyasi.write(");\n\n")

    for url_il, gercek_il in iller_map.items():
        print(f"{gercek_il} ili genel eczaneleri taranıyor...")
        url = f"https://www.eczaneler.gen.tr/eczaneler/{url_il}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.text, "html.parser")
            
            tablolar = soup.find_all("table")
            
            if not tablolar:
                print(f"{gercek_il} için tablo bulunamadı.")
                continue

            for tablo in tablolar:
                satirlar = tablo.find_all("tr")
                for satir in satirlar:
                    satir_metni = satir.get_text(separator=" | ", strip=True)
                    
                    if not re.search(r"0\s*\(\d{3}\)\s*\d{3}-\d{2}-\d{2}", satir_metni):
                        continue
                        
                    parcalar = [p.strip() for p in satir_metni.split(" | ") if p.strip()]
                    eczane_adi = guvenli_sql(parcalar[0], 150)
                    
                    # İç içe tablo sorununu (yığılmayı) engelleyen zırhlı algoritma
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
                                # Telefon numarasından sonra gelen metinler, içine gizlenmiş DİĞER eczanedir. Döngüyü kır!
                                break 
                            else:
                                adres_parcalari.append(p)
                                
                    if not telefonlar_listesi:
                        continue
                        
                    telefon_metni = guvenli_sql(" - ".join(telefonlar_listesi), 255)
                    ham_adres = " ".join(adres_parcalari)
                    adres_sql = guvenli_sql(ham_adres)
                    
                    ilce = ""
                    match = re.search(r"/\s*" + re.escape(gercek_il), ham_adres, re.IGNORECASE)
                    if match:
                        oncesi = ham_adres[:match.start()].strip()
                        oncesi = oncesi.rstrip(",.-")
                        kelimeler = oncesi.split()
                        if kelimeler:
                            ilce = kelimeler[-1]
                            if ilce.lower() == "merkez":
                                ilce = f"{gercek_il} Merkez"
                                
                    ilce_sql = guvenli_sql(ilce, 100)
                    sehir_sql = guvenli_sql(gercek_il, 100)
                    eczane_id = str(uuid.uuid4())

                    insert_sorgusu = f"INSERT INTO eczaneler (eczane_id, ad, adres, sehir, ilce, telefon) VALUES ('{eczane_id}', '{eczane_adi}', '{adres_sql}', '{sehir_sql}', '{ilce_sql}', '{telefon_metni}');\n"
                    sql_dosyasi.write(insert_sorgusu)
            
            time.sleep(1)

        except Exception as e:
            print(f"{gercek_il} verileri çekilirken bir hata oluştu: {e}")

    print("\nİşlem tamamlandı!")