/**
 * TC Kimlik Numarasi (TCKN) checksum dogrulamasi.
 *
 * `backend/app/core/tckn.py::tckn_checksum_valid`'in BIREBIR ayni mod-10
 * formulu - sadece dogrulama, hash/pepper YOK (o backend'e ozel, tam
 * numara burada hicbir yere kalici yazilmaz, sadece OCR'dan cikan aday
 * numaralari ayirt etmek icin kullanilir - bkz. IdCardScanner.tsx).
 */
export function tcknChecksumValid(numara: string): boolean {
  if (!/^\d{11}$/.test(numara)) {
    return false;
  }

  const haneler = numara.split("").map(Number);
  const tekToplam = haneler[0] + haneler[2] + haneler[4] + haneler[6] + haneler[8]; // 1.,3.,5.,7.,9.
  const ciftToplam = haneler[1] + haneler[3] + haneler[5] + haneler[7]; // 2.,4.,6.,8.

  if ((tekToplam * 7 - ciftToplam) % 10 !== haneler[9]) {
    return false;
  }

  const ilkOnHanelerToplami = haneler.slice(0, 10).reduce((a, b) => a + b, 0);
  return ilkOnHanelerToplami % 10 === haneler[10];
}
