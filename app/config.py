from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Bot
    BOT_TOKEN: str

    # Database (asyncpg dsn, e.g. postgresql+asyncpg://user:pass@host:5432/dbname)
    DATABASE_URL: str

    # Comma-separated Telegram IDs that get super_admin role on first /start
    SUPER_ADMIN_IDS: str = ""

    # If True, moderator-created events need super_admin approval before going active
    REQUIRE_EVENT_APPROVAL: bool = True

    @property
    def super_admin_ids(self) -> list[int]:
        return [int(x) for x in self.SUPER_ADMIN_IDS.split(",") if x.strip()]


settings = Settings()

# Fixed interest categories (MVP — no free text, per TZ decision)
INTEREST_CATEGORIES = [
    "IT",
    "Business",
    "Design",
    "Debate",
    "Marketing",
    "Career",
    "Volunteering",
    "Sport",
]

# Fixed event formats (per TZ section 5)
EVENT_FORMATS = [
    "Networking",
    "Debate",
    "Masterclass",
    "Workshop",
    "Business Challenge",
    "Quiz",
    "Game Night",
    "Movie Night",
    "Guest Speaker",
    "Career Meeting",
    "University Meetup",
]

# Fixed university list — MVP starting set (per TZ section 1).
# Adding a new university = editing this list only, no code change elsewhere.
UNIVERSITIES = [
    "TDIU",
    "WIUT",
    "INHA",
    "Webster",
    "Turin",
    "MDIS",
    "TEAM",
    "Yeoju",
    "Amity",
]
