# GATİM - Envanter ve Talep Takip Sistemi Güvenlik İnceleme Raporu

## Kontrol: Şifre Güvenliği
Durum: Başarılı
İlgili Dosyalar: [app/models.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/models.py) (User model), [app/auth/routes.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/auth/routes.py)
Açıklama: Kullanıcı şifreleri veritabanında hiçbir zaman düz metin (plain-text) olarak saklanmaz. `Werkzeug` kütüphanesinin `generate_password_hash` ve `check_password_hash` metotları kullanılarak PBKDF2 standardında güvenli bir şekilde tuzlanıp (salted) hash'lenir. Şifre doğrulama işlemleri de bu hash üzerinden gerçekleştirilir.

---

## Kontrol: CSRF
Durum: Başarılı
İlgili Dosyalar: [app/__init__.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/__init__.py), [app/auth/forms.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/auth/forms.py), [app/inventory/forms.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/inventory/forms.py), [app/requests/forms.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/requests/forms.py), Tüm HTML Form Şablonları.
Açıklama: Uygulamadaki tüm durum değiştiren formlar (login, register, malzeme ekleme/düzenleme, talep onay/red/teslimat/iptal) Flask-WTF entegrasyonu ve CSRFProtect uzantısı ile korunmaktadır. Form şablonlarına `{{ form.hidden_tag() }}` veya `csrf_token()` eklenerek Cross-Site Request Forgery saldırıları engellenmiştir.

---

## Kontrol: Yetki Kontrolü
Durum: Başarılı
İlgili Dosyalar: [app/auth/decorators.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/auth/decorators.py), [app/admin/routes.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/admin/routes.py), [app/inventory/routes.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/inventory/routes.py), [app/requests/routes.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/requests/routes.py)
Açıklama: `@role_required` dekoratörü kullanılarak Rol Tabanlı Erişim Kontrolü (RBAC) uygulanmıştır. Normal çalışanlar admin sayfalarına ve malzeme ekleme/düzenleme/onaylama/teslim etme yetki limitlerine erişemez. Yetkisiz istekler 403 Forbidden status kodu döndürülerek engellenir. Kullanıcıların kendi talepleri dışındaki talepleri iptal etmeye çalışması durumunda sahiplik kontrolleri yapılmaktadır.

---

## Kontrol: SQL Injection
Durum: Başarılı
İlgili Dosyalar: [app/models.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/models.py), [app/inventory/routes.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/inventory/routes.py), [app/requests/routes.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/requests/routes.py)
Açıklama: SQL sorguları doğrudan ham metin (raw SQL) olarak çalıştırılmamaktadır. Tamamen SQLAlchemy ORM yapısı ve parametrik sorgu (parametrized queries) kullanan Select cümleleri tercih edilmiştir. Bu sayede kullanıcı girişleri otomatik olarak sanitize edilir ve SQL injection olasılığı tamamen ortadan kalkar.

---

## Kontrol: env Güvenliği
Durum: Başarılı
İlgili Dosyalar: [config.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/config.py), [run.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/run.py), `.env` (Örnek)
Açıklama: Uygulama ayarları (veritabanı bağlantısı, gizli anahtarlar, debug parametreleri) doğrudan kod içerisine gömülmeyip `python-dotenv` kütüphanesi yardımıyla ortam değişkenlerinden (environment variables) veya `.env` dosyasından yüklenir. Hassas verilerin kaynak kod deposuna sızması engellenmiştir.

---

## Kontrol: SECRET_KEY
Durum: Başarılı
İlgili Dosyalar: [config.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/config.py), `.env`
Açıklama: Flask session güvenliğini, CSRF token üretimini ve şifreleme işlemlerini kontrol eden `SECRET_KEY` parametresi konfigurasyon dosyasında güvenli bir fallback değerle yüklenmekte ve canlı ortamlarda mutlaka `.env` dosyasından okunacak şekilde tasarlanmıştır.

---

## Kontrol: API Güvenliği
Durum: Başarılı
İlgili Dosyalar: [app/api/routes.py](file:///c:/Users/kerem/Desktop/gatim_envanter_sistemi/app/api/routes.py)
Açıklama: `/api/v1` altındaki tüm JSON API uç noktaları `@login_required` ile korunmaktadır. API'ler sadece kendi yetki alanlarındaki JSON verilerini döner. Dönülen JSON nesnelerinde hiçbir zaman kullanıcı şifre hash'leri, e-posta adresleri veya kişisel gizli veriler dışarı sızdırılmaz.
