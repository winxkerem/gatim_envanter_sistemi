# GATİM - Envanter ve Talep Takip Sistemi

Gazi Teknoloji ve İnovasyon Merkezleri A.Ş. (GATİM) için geliştirilmiş modern Envanter Yönetimi ve Personel Malzeme Talep Takip Sistemi.

---

## Projenin Amacı
Bu projenin amacı, GATİM bünyesindeki bilişim ekipmanları, altyapı bileşenleri ve sarf malzemelerinin dijital envanter kaydını tutmak; personelin ihtiyaç duyduğu malzemeler için kolayca talep oluşturmasını sağlamak ve yöneticilerin bu talepleri onay/teslimat süreçlerine göre takip edebileceği entegre bir sistem sunmaktır.

---

## Kullanılan Teknolojiler
- **Web Çatısı**: Flask 3.x
- **Veritabanı ORM**: Flask-SQLAlchemy 3.1+ (SQLAlchemy 2.x Declarative Mapped Mimarisi)
- **Veritabanı Göçleri (Migration)**: Flask-Migrate 4.x
- **Oturum Yönetimi**: Flask-Login 0.6+
- **Form & Güvenlik**: Flask-WTF (CSRF Protection)
- **Şifreleme**: Werkzeug (PBKDF2 Hashing)
- **Test Çatısı**: Pytest 9.x
- **Konteynerleştirme**: Docker & Docker Compose

---

## Roller ve Yetkiler
1. **Admin (Yönetici)**: Tam yetki. Kullanıcı rolleri güncelleme, envanter ekleme/düzenleme, tüm talepleri onaylama/reddetme/teslim etme.
2. **Envanter Sorumlusu (Inventory Manager)**: Envantere malzeme ekleme/düzenleme, tüm talepleri listeleme, onaylama, reddetme ve teslim etme.
3. **Personel (Employee / User)**: Envanteri arama/görüntüleme, talep oluşturma, kendi taleplerini listeleme ve "pending" durumundaki kendi taleplerini iptal etme.

---

## Veritabanı Modelleri
- **Department**: Departman bilgisi.
- **User**: Sistem kullanıcıları (Kullanıcı adı, e-posta, rol, şifre hash'i).
- **Category**: Malzeme kategorileri.
- **InventoryItem**: Stok bilgileri, kritik seviye uyarı limitleri ve kategori eşleşmesi.
- **InventoryRequest**: Personel talepleri (Miktar, durum bilgisi: pending/approved/delivered/rejected).
- **RequestLog**: Taleplerin tüm durum değişikliklerinin audit logları.

---

## Kurulum

1. Depoyu klonlayın veya çalışma dizinine gidin.
2. Sanal ortam oluşturup aktif edin:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # macOS/Linux
   ```
3. Bağımlılıkları yükleyin:
   ```bash
   pip install -r requirements.txt
   ```

---

## .env Ayarları
Proje kök dizininde bir `.env` dosyası oluşturun ve aşağıdaki değişkenleri tanımlayın:
```env
SECRET_KEY=gatim-cok-gizli-anahtar-1234
FLASK_DEBUG=True
FLASK_RUN_PORT=5000
DATABASE_URL=sqlite:///gatim_inventory.db
```

---

## Migration Komutları
Veritabanı şemasını oluşturmak ve migration yapısını kurmak için:
```bash
$env:FLASK_APP="run.py"  # Windows PowerShell
# veya set FLASK_APP=run.py (Windows CMD)
# veya export FLASK_APP=run.py (macOS/Linux)

# 1. Migration yapısını kurun
flask db init

# 2. Migration şeması oluşturun
flask db migrate -m "Initial migration"

# 3. Şemayı veritabanına uygulayın
flask db upgrade
```

---

## Uygulamayı Çalıştırma
Öncelikle veritabanını test verileri ile beslemek için seeder komutunu çalıştırın:
```bash
flask seed-db
```
Ardından uygulamayı başlatın:
```bash
python run.py
```
Uygulamaya tarayıcınızdan `http://localhost:5000` adresinden erişebilirsiniz.

---

## Docker ile Çalıştırma
Uygulamayı Docker konteynerleri üzerinde ayağa kaldırmak için:
```bash
docker-compose up --build
```
Konteyner içindeki veritabanını seed etmek isterseniz:
```bash
docker-compose exec web flask seed-db
```

---

## Testleri Çalıştırma
Tüm birim ve entegrasyon testlerini çalıştırmak için:
```bash
python -m pytest
```

---

## API Endpointleri
API uç noktalarına erişmek için oturum açmış olmanız gerekmektedir:
- `GET /api/v1/items`: Sistemdeki tüm envanter kalemlerini JSON formatında döndürür.
- `GET /api/v1/requests/my`: Giriş yapmış olan kullanıcının tüm taleplerini JSON formatında döndürür.

---

## Demo Videosu
Proje demo videosuna aşağıdaki bağlantı üzerinden erişebilirsiniz:
- [GATİM Envanter Sistemi Demo Videosu] https://youtu.be/SU_zvkN-s_E

---

## AI Kullanım Süreci
Bu projenin geliştirilmesinde AI asistanı pair programming mantığıyla kullanılmıştır:
- SQLAlchemy 2.x Mapped Declarative modellerinin oluşturulması.
- Envanter arama filtreleri ve Flask-SQLAlchemy 3.x pagination mimarisi.
- pytest-flask birim test yapısının entegrasyonu.
- AI sürecinde karşılaşılan `ModuleNotFoundError` ve test oturumu temizleme (IntegrityError session clear) gibi hatalar analiz edilerek çözülmüştür.
