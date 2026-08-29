# THE SOCIETY — Backend + Bot (1-bosqich)

Students from different universities, one community.

## Arxitektura

- **`app/`** — umumiy backend logikasi (DB modellari, biznes logika). Bot ham,
  keyinroq qo'shiladigan Telegram Mini App ham shu qatlamdan foydalanadi —
  `app/crud.py` ikkalasi uchun ham umumiy bo'ladi.
- **`bot/`** — aiogram 3.x bot: onboarding, events, registratsiya, admin panel.
- **`main.py`** — ishga tushirish nuqtasi (`python main.py`).

## O'rnatish

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env faylni to'ldiring: BOT_TOKEN, DATABASE_URL, SUPER_ADMIN_IDS
```

PostgreSQL o'rnatilgan va ishlab turgan bo'lishi kerak. Jadvallar birinchi
ishga tushirishda avtomatik yaratiladi (`init_db()` — MVP uchun yetarli,
keyinroq Alembic migratsiyalariga o'tish tavsiya etiladi).

```bash
python main.py
```

## Funksional (1-bosqich)

- `/start` — onboarding: ism → universitet → qiziqishlar (fixed kategoriyalar)
- `/events` — faol eventlar ro'yxati, tafsilot, ro'yxatdan o'tish
- `/my` — mening registratsiyalarim, bekor qilish
- `/admin` — Super Admin / Moderator panel:
  - Event yaratish (moderator eventi `pending` holatda, super admin tasdiqlaydi —
    `.env` dagi `REQUIRE_EVENT_APPROVAL` bilan boshqariladi)
  - Mening eventlarim, bekor qilish (moderator faqat o'z eventini)
  - Ishtirokchilar ro'yxatini CSV qilib olish
  - Statistika (super admin uchun)

## Race-condition himoyasi

`app/crud.py :: register_for_event` — event qatorini `SELECT ... FOR UPDATE`
bilan bloklaydi, shu orqali oxirgi joy uchun bir vaqtda kelgan ikkita
registratsiya so'rovi ikkalasi ham muvaffaqiyatli bo'lib ketmaydi.

## Keyingi qadam — Telegram Mini App

`app/crud.py` funksiyalari to'g'ridan-to'g'ri FastAPI endpointlariga
o'ralishi mumkin (masalan `GET /events` → `crud.list_active_events`).
Auth uchun Telegram WebApp `initData` tekshiruvi qo'shiladi — alohida
login/parol tizimi kerak emas.

## Hali qilinmagan (keyingi iteratsiyada)

- Avtomatik eslatma (reminder) — event vaqtidan oldin foydalanuvchiga xabar
- Til tanlovi (UZ/RU/EN) — `User.language` maydoni tayyor, lekin handlerlar
  hozircha faqat o'zbek tilida javob beradi
- Monitoring/uptime alert
