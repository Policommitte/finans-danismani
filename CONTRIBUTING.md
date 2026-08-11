# Katkı Rehberi

## Branch stratejisi

`main` korumalıdır — doğrudan push kapalı, sadece PR ile birleşir.

Branch isimlendirme:
```
feature/FR-PORT-01-portfoy-ozeti
fix/chat-streaming-kopmasi
chore/ci-guncelleme
```

## Commit mesajları

Conventional Commits kullanın:
```
feat(portfolio): portföy özeti endpoint'i eklendi
fix(chat): streaming yanıtta kopma giderildi
docs(readme): kurulum adımları güncellendi
chore(ci): lint adımı eklendi
```

Tipler: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Pull request kuralları

- Küçük tutun — 400 satırdan büyük PR'lar geç review alır.
- En az 1 onay gerekir, CI yeşil olmalıdır.
- Açıklamada ilgili gereksinim ID'sini (FR-XXX-NN) yazın.
- Kendi PR'ınızı kendiniz merge edin (onay aldıktan sonra).

## Kod standartları

**Backend:** ruff (lint) + black (format). Commit öncesi `ruff check . && black .`
**Frontend:** eslint + prettier.

## Gizli bilgiler

API anahtarları ve şifreler `.env` dosyasında tutulur, asla commit edilmez.
Yeni bir değişken eklerseniz `.env.example` dosyasına da (değersiz olarak) ekleyin.
