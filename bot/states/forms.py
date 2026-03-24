"""
FSM states for multi-step flows.
"""
from aiogram.fsm.state import State, StatesGroup


class ProfileState(StatesGroup):
    """Profile update: full name, phone."""

    full_name = State()
    phone = State()


class GraveState(StatesGroup):
    """Add grave: region, district, cemetery, deceased, birth (choice->year[/month]), death, relationship."""

    region = State()
    district = State()
    cemetery = State()
    deceased_full_name = State()
    birth_choice = State()  # Aniq or Taxminan
    birth_year = State()
    birth_month = State()  # only if Aniq
    death_choice = State()
    death_year = State()
    death_month = State()  # only if Aniq
    relationship_status = State()


class LanguageState(StatesGroup):
    """Language selection (for new users)."""

    waiting = State()


class RegistrationState(StatesGroup):
    """Mandatory registration: full name, phone number."""

    full_name = State()
    phone = State()


class CheckoutState(StatesGroup):
    """Checkout: full name, phone, region, district, cemetery, deceased, years, comment."""

    full_name = State()
    phone_number = State()
    region = State()
    district = State()
    cemetery = State()
    deceased_full_name = State()
    birth_year = State()
    death_year = State()
    comment = State()
    confirm = State()


class PaymentState(StatesGroup):
    """Payment: select method, upload receipt screenshot."""

    select_method = State()
    upload_receipt = State()


class SupportState(StatesGroup):
    """Support: user writes message."""

    waiting_for_message = State()


class FlowerCheckoutState(StatesGroup):
    """Flower order form: first name, last name, birth year, death year."""

    first_name = State()
    last_name = State()
    birth_year = State()
    death_year = State()
    confirm = State()


class FlowerPaymentState(StatesGroup):
    """Flower payment: upload receipt screenshot."""

    upload_receipt = State()


class ComplaintState(StatesGroup):
    """Complaint: user writes complaint text."""

    waiting_for_text = State()


class RatingCommentState(StatesGroup):
    """Rating: optional comment after like/dislike."""

    waiting_comment = State()


class OrderCheckoutState(StatesGroup):
    """Order checkout from cart: region, district, cemetery, deceased, years."""

    region = State()
    district = State()
    cemetery = State()
    deceased_full_name = State()
    birth_year = State()
    death_year = State()
    confirm = State()


class UserSubmissionState(StatesGroup):
    """User submission flow: name, phone, relationship, 2 photos."""

    full_name = State()
    phone = State()
    relationship = State()
    photo_1 = State()
    photo_2 = State()
