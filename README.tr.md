# Banka–Muhasebe Mutabakat ve Finansal Kontrol Sistemi

Banka hareketlerini, dönem başı açık faturaları ve muhasebe fişlerini birlikte
kontrol eden, yerel bilgisayarda çalışan bir portföy uygulaması.

**Geliştiren: Murat Miraç Gedik**

## Çalıştırma
Python 3.11+ kurulu olmalı. Harici Python paketi gerekmez.
Depoyu ZIP olarak indirip çıkartın. Klasörde terminal açın:

```bash
python app.py
```

Tarayıcıda **http://127.0.0.1:8765** adresini açın. `Load synthetic demo` ile örneği
çalıştırın veya üç CSV yükleyin. Windows'ta `py app.py` de kullanılabilir.

## İşlevler
- Bire bir, bölünmüş ve toplu ödemelerin referans temelli eşleştirilmesi.
- Tutar, tarih, taraf, para birimi ve muhasebe fişi kontrolleri.
- Mükerrer kayıt şüphesi, komisyon farkı, eksik/fazla ödeme ve açık faturalar.
- Referansı olmayan işlemlerde yalnızca tekil adaylar için inceleme önerisi.
- Durum filtresi, arama, kayıt ayrıntısı, CSV ve JSON raporları.

Örnekte 53 banka hareketi, 53 fatura ve 105 muhasebe satırı vardır.
43 grup eşleşir, 6 grup incelemeye ayrılır; 8 kontrol istisnası üretilir.
Bunlar sentetik test sonuçlarıdır; gerçek veride başarı oranı iddiası değildir.

## Ekran terimleri
| Terim | Anlamı |
|---|---|
| MATCHED | Üç kaynak politika sınırları içinde uyuşuyor |
| REVIEW | İnsan incelemesi gerekli |
| Unresolved gross | Eşleşmeyen banka hareketlerinin mutlak tutar toplamı |
| Difference | Banka tutarı eksi açık fatura tutarı |
| Evidence strength | Kural gücü; istatistiksel olasılık değildir |

CSV/JSON raporlarında tutarlar kuruş/cent cinsinden tam sayıdır. Örneğin 112500,
1.125,00 TL anlamına gelir. Ekran tutarları normal para biriminde gösterir.

Dosyalar diske kaydedilmez, üçüncü taraf servislere gönderilmez. İndirilen raporlar
ise girdi kimliklerini içerir; gerçek finansal dosyaları GitHub'a eklemeyin.
Bu sürüm muhasebe kaydı oluşturmaz, ödeme yapmaz ve onay kararı vermez.

[Veri sözleşmesi](docs/DATA_CONTRACT.md) · [Yöntem](docs/METHODOLOGY.md) · [English](README.md)

## Eşleştirme nasıl çalışır?
1. Dosya başlıkları, kayıt kimlikleri, tarih ve tutarlar doğrulanır.
2. Aynı iş alanlarına sahip mükerrer kayıt adayları ayrılır.
3. Her muhasebe fişinin borç/alacak dengesi para birimi bazında kontrol edilir.
4. BANK satırlarının net tutarı ilgili banka hareketiyle karşılaştırılır.
5. Fatura referanslarıyla bağlı ödeme grupları kurulur; bölünmüş ve toplu ödemeler birlikte ele alınır.
6. Referans, taraf, tarih, para birimi ve muhasebe kontrolleri geçen gruplar MATCHED olur.
7. Belirsiz, eksik veya fark içeren gruplar incelemeye bırakılır.

| Örnek kayıt | Senaryo | Beklenen sonuç |
|---|---|---|
| B041 / B042 | Bir faturanın iki ödemeyle kapatılması | MATCHED |
| B043 | İki faturanın tek ödemeyle kapatılması | MATCHED |
| B044 | Komisyon kesintisi | REVIEW; farkın açıklaması gösterilir |
| B045 | Kısmi ödeme | REVIEW |
| B046 / B047 | Mükerrer işlem şüphesi | İki kayıt da incelemeye ayrılır |
| B048 | Muhasebe kaydı eksik | REVIEW |
| B049 | Referanssız tekil aday | REVIEW; kesin eşleşme sayılmaz |
| B050 | Birden fazla aday fatura | Atama yapılmaz |

## Veri hazırlığı ve toleranslar
CSV başlıkları örnek dosyalarla aynı olmalıdır. Tarihler YYYY-MM-DD, tutarlar noktalı
ondalık biçimde yazılır. Fatura tutarı dönem başı açık bakiyedir. Pozitif değerler
alacak/tahsilatı, negatif değerler borç/ödemeyi gösterir. Taraf kimlikleri eşit olmalıdır.

Varsayılan tarih penceresi 45 gün, tutar toleransı 1 kuruş/cent'tir. Muhasebe BANK
satırı karşılaştırması tam eşitlik arar. TRY, USD, EUR ve GBP ayrı değerlendirilir;
kur dönüşümü veya para birimleri arasında mahsuplaşma yapılmaz.

## Rapor ve kanıt
JSON; çalışma kimliğini, girdi SHA-256 özetlerini, politikayı, grupları, istisnaları
ve para birimi toplamlarını içerir. CSV yalnızca mutabakat gruplarını içerir.
İstisnalar çakışabilir; adetlerini inceleme gruplarıyla toplamak doğru değildir.
Dosya özeti anonimleştirme veya değiştirilemez denetim kaydı anlamına gelmez.

## Komut satırı
```bash
python -m reconcile --demo --output output
python -m reconcile --input data/demo --output output --days 45 --tolerance 1
python -m unittest discover -s tests -v
```

## Güvenlik ve bakım
İş akışları sabit commit kimliklerine bağlanmıştır. CI yalnızca okuma yetkisiyle
çalışır; CodeQL işlerinin tarama sonucu yükleme yetkisi vardır. Checkout kimlik
bilgilerini kalıcı tutmaz. Python ve JavaScript ayrı CodeQL işlerinde taranır.
CODEOWNERS dosyası kod sahibini belirtir; zorunlu onay için GitHub kural ayarları gerekir.

Secret scanning, push protection ve dal koruması depo ayarlarıdır; dosyalardaki
korumalar bunların açık olduğunu tek başına kanıtlamaz. [Güvenlik politikası](SECURITY.md).

## Sınırlar
30 otomatik test ve tekrarlanabilir sentetik sonuç kontrolü bulunur. Gerçek veride
başarı oranı ölçülmemiştir. Tarayıcı görsel testi ilk geliştirme ortamında Chromium
indirme sorunu nedeniyle tamamlanamamıştır. Kalıcı inceleme/onay kaydı, ERP bağlantısı,
kur dönüşümü ve bankaya özel dosya dönüştürücüleri bu sürümde yoktur.
