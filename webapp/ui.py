"""UI yordamchilari — narx formati, holat nomlari (o'zbekcha)."""

ORDER_STATUS_LABELS = {
    "new": "Yangi",
    "pending_payment": "To'lov kutilmoqda",
    "payment_review": "To'lov tekshirilmoqda",
    "paid": "To'langan",
    "in_progress": "Bajarilmoqda",
    "completed": "Bajarildi",
    "cancelled": "Bekor qilingan",
    "feedback_pending": "Izoh kutilmoqda",
}

ORDER_STATUS_COLORS = {
    "new": "#6b7280",
    "pending_payment": "#d97706",
    "payment_review": "#d97706",
    "paid": "#2563eb",
    "in_progress": "#2563eb",
    "completed": "#16a34a",
    "cancelled": "#dc2626",
    "feedback_pending": "#d97706",
}

RELATIONSHIP_LABELS = {
    "Grandmother": "Buvi",
    "Grandfather": "Bobo",
    "Mother": "Ona",
    "Father": "Ota",
    "Brother": "Aka/uka",
    "Sister": "Opa/singil",
    "Uncle": "Tog'a/amaki",
    "Aunt": "Xola/amma",
    "Other": "Boshqa",
    "Blood Relative": "Qarindosh",
}


def format_price(value: int | None) -> str:
    """Narxni '1 500 000 so'm' ko'rinishida formatlaydi."""
    if not value:
        return "0 so'm"
    return f"{int(value):,}".replace(",", " ") + " so'm"


def status_label(status: str) -> str:
    return ORDER_STATUS_LABELS.get(status, status)


def status_color(status: str) -> str:
    return ORDER_STATUS_COLORS.get(status, "#6b7280")


def relationship_label(value: str) -> str:
    return RELATIONSHIP_LABELS.get(value, value)


def format_years(birth: int | None, death: int | None) -> str:
    """Tug'ilgan-vafot yillarini '1940 - 2010' ko'rinishida."""
    if birth and death:
        return f"{birth} - {death}"
    if birth:
        return f"{birth} - ?"
    if death:
        return f"? - {death}"
    return ""


# Buyurtma holati ketma-ketligi (yangidan bajarilgangacha)
_STATUS_SEQUENCE = [
    "new", "pending_payment", "payment_review", "paid", "in_progress", "completed",
]


def order_steps(order) -> list[dict]:
    """Buyurtma holati bosqichlari — har biri 'done' bayrog'i bilan."""
    rank = {s: i for i, s in enumerate(_STATUS_SEQUENCE)}
    cur = rank.get(order.status, 0)
    definitions = [
        ("Buyurtma berildi", 0),
        ("To'lov tekshirilmoqda", 2),
        ("To'lov tasdiqlandi", 3),
        ("Ishchi qabul qildi", 4),
        ("Ish bajarildi", 5),
    ]
    return [{"label": label, "done": cur >= need} for label, need in definitions]
