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
