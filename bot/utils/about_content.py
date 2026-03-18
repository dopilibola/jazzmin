"""
About Us content. Structured for easy migration to database or admin panel later.
Currently static; replace get_about_content() with DB lookup when needed.
"""
from typing import TypedDict


class AboutSection(TypedDict):
    """Structure for About Us sections. Can map to DB columns later."""

    title: str
    mission: str
    how_it_works: str


# Static content. Later: fetch from DB or admin panel.
ABOUT_CONTENT: dict[str, AboutSection] = {
    "en": {
        "title": "🏛 Grave Care Service",
        "mission": (
            "Our mission is to provide dignified and respectful care "
            "for graves and memorial sites."
        ),
        "how_it_works": (
            "How we work:\n"
            "• You choose a service (cleaning, flowers, soil renewal)\n"
            "• We schedule and perform the work\n"
            "• You receive a photo report upon completion\n"
            "• You can rate our work and stay in touch via support\n\n"
            "We are here to help. Contact us anytime."
        ),
    },
    "ru": {
        "title": "🏛 Сервис ухода за могилами",
        "mission": (
            "Наша миссия — обеспечивать достойный и уважительный уход "
            "за могилами и памятными местами."
        ),
        "how_it_works": (
            "Как мы работаем:\n"
            "• Вы выбираете услугу (уборка, цветы, обновление грунта)\n"
            "• Мы планируем и выполняем работу\n"
            "• Вы получаете фотоотчёт по завершении\n"
            "• Вы можете оценить нашу работу и связаться с нами через поддержку\n\n"
            "Мы всегда готовы помочь. Свяжитесь с нами в любое время."
        ),
    },
    "uz": {
        "title": "🏛 Qabr parvarish xizmati",
        "mission": (
            "Bizning vazifamiz — qabrlarni va yodgorlik joylarini "
            "qadrli va hurmatli parvarish qilish."
        ),
        "how_it_works": (
            "Qanday ishlaymiz:\n"
            "• Siz xizmatni tanlaysiz (tozalash, gullar, tuproq yangilash)\n"
            "• Biz rejalashtiramiz va ishni bajaramiz\n"
            "• Tugagach foto hisobot olasiz\n"
            "• Ishni baholashingiz va qo'llab-quvvatlash orqali bog'lanishingiz mumkin\n\n"
            "Yordam berishga tayyormiz. Istalgan vaqtda bog'laning."
        ),
    },
}


def get_about_content(lang: str) -> str:
    """
    Get formatted About Us content for the given language.
    Fallback to English if lang not found.
    TODO: Replace with DB lookup when admin panel is added.
    """
    content = ABOUT_CONTENT.get(lang, ABOUT_CONTENT["en"])
    return f"{content['title']}\n\n{content['mission']}\n\n{content['how_it_works']}"
