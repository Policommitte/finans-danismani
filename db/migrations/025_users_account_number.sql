-- TCKN/NVI dogrulamali kayit akisi kaldirildi; yeni akis banka hesabi
-- baglama SIMULASYONUNDA bir hesap numarasi topluyor. Bu alan dogrulanmaz,
-- yalnizca bilgi amacli saklanir - bu yuzden NULL'a izin verilir ve UNIQUE
-- kisitlamasi YOKTUR (ayni numara birden fazla kullanicida gorunebilir,
-- gercek bir banka baglantisi degildir).
--
-- Onceden eklenen tckn_hash/tckn_last4/birth_date/phone_number kolonlari
-- KALDIRILMAZ (veri kaybini onlemek icin) - yeni kayit akisi onlari
-- kullanmaz, eski hesaplar icin veri olarak durur.
ALTER TABLE users ADD COLUMN IF NOT EXISTS account_number VARCHAR(9);
