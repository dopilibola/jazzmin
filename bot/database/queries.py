"""
Database CRUD helpers. All functions are async and expect an AsyncSession.
"""
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from bot.database.models import (
    Cart,
    CartItem,
    Cemetery,
    District,
    Flower,
    FlowerCategory,
    FlowerProduct,
    Grave,
    Order,
    OrderItem,
    Rating,
    Region,
    Service,
    SupportMessage,
    User,
)
from bot.database.models import (
    ORDER_STATUS_NEW,
    ORDER_STATUS_PAYMENT_REVIEW,
    RELATIONSHIP_DEFAULT,
)


# -----------------------------------------------------------------------------
# User
# -----------------------------------------------------------------------------


async def get_user_by_telegram_id(session, telegram_id: int) -> User | None:
    """Get user by Telegram ID."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def register_user(
    session,
    telegram_id: int,
    *,
    language: str | None = None,
    full_name: str | None = None,
    phone_number: str | None = None,
) -> User:
    """Register or get existing user. Alias for create_or_update_user."""
    return await create_or_update_user(
        session, telegram_id,
        language=language, full_name=full_name, phone_number=phone_number,
    )


async def create_or_update_user(
    session,
    telegram_id: int,
    *,
    language: str | None = None,
    full_name: str | None = None,
    phone_number: str | None = None,
) -> User:
    """Create or update user. Returns the user."""
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            language=language or "ru",
            full_name=full_name or "",
            phone_number=phone_number or "",
        )
        session.add(user)
    else:
        if language is not None:
            user.language = language
        if full_name is not None:
            user.full_name = full_name
        if phone_number is not None:
            user.phone_number = phone_number
    await session.flush()
    await session.refresh(user)
    return user


async def update_profile(
    session,
    telegram_id: int,
    *,
    full_name: str | None = None,
    language: str | None = None,
    phone_number: str | None = None,
) -> User | None:
    """Update user profile. Returns user or None if not found."""
    user = await get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return None
    if full_name is not None:
        user.full_name = full_name
    if language is not None:
        user.language = language
    if phone_number is not None:
        user.phone_number = phone_number
    await session.flush()
    await session.refresh(user)
    return user


# -----------------------------------------------------------------------------
# Graves
# -----------------------------------------------------------------------------


async def add_grave(
    session,
    user_id: int,
    *,
    region: str,
    district: str,
    cemetery: str,
    deceased_full_name: str,
    birth_year: int | None = None,
    birth_month: int | None = None,
    birth_approximate: bool = False,
    death_year: int | None = None,
    death_month: int | None = None,
    death_approximate: bool = False,
    relationship_status: str | None = None,
) -> Grave:
    """Add a grave for user. Returns the created grave."""
    grave = Grave(
        user_id=user_id,
        region=region,
        district=district,
        cemetery=cemetery,
        deceased_full_name=deceased_full_name,
        birth_year=birth_year,
        birth_month=birth_month,
        birth_approximate=birth_approximate,
        death_year=death_year,
        death_month=death_month,
        death_approximate=death_approximate,
        relationship_status=relationship_status or RELATIONSHIP_DEFAULT,
    )
    session.add(grave)
    await session.flush()
    await session.refresh(grave)
    return grave


async def list_user_graves(session, user_id: int) -> list[Grave]:
    """List all graves for user (by users.id, not telegram_id)."""
    result = await session.execute(
        select(Grave).where(Grave.user_id == user_id).order_by(Grave.id)
    )
    return list(result.scalars().all())


async def get_grave_by_id(session, grave_id: int, user_id: int) -> Grave | None:
    """Get grave by ID if it belongs to user."""
    result = await session.execute(
        select(Grave).where(Grave.id == grave_id, Grave.user_id == user_id)
    )
    return result.scalar_one_or_none()


# -----------------------------------------------------------------------------
# Service, Flower
# -----------------------------------------------------------------------------


async def get_all_services(session) -> list[Service]:
    """Get all services ordered by id."""
    result = await session.execute(select(Service).order_by(Service.id))
    return list(result.scalars().all())


async def get_service_by_id(session, service_id: int) -> Service | None:
    """Get service by ID."""
    result = await session.execute(select(Service).where(Service.id == service_id))
    return result.scalar_one_or_none()


async def get_all_flowers(session) -> list[Flower]:
    """Get all flowers ordered by id."""
    result = await session.execute(select(Flower).order_by(Flower.id))
    return list(result.scalars().all())


async def get_flower_by_id(session, flower_id: int) -> Flower | None:
    """Get flower by ID."""
    result = await session.execute(select(Flower).where(Flower.id == flower_id))
    return result.scalar_one_or_none()


# -----------------------------------------------------------------------------
# Flower Categories and Products (flower feature module)
# -----------------------------------------------------------------------------


async def get_all_flower_categories(session) -> list[FlowerCategory]:
    """Get all flower categories with products."""
    result = await session.execute(
        select(FlowerCategory).order_by(FlowerCategory.id)
    )
    return list(result.scalars().all())


async def get_flower_category_by_id(session, category_id: int) -> FlowerCategory | None:
    """Get flower category by ID with products."""
    result = await session.execute(
        select(FlowerCategory)
        .where(FlowerCategory.id == category_id)
    )
    return result.scalar_one_or_none()


async def get_flower_products_by_category(
    session, category_id: int
) -> list[FlowerProduct]:
    """Get flower products for a category."""
    result = await session.execute(
        select(FlowerProduct)
        .where(FlowerProduct.category_id == category_id)
        .order_by(FlowerProduct.id)
    )
    return list(result.scalars().all())


async def get_flower_product_by_id(session, product_id: int) -> FlowerProduct | None:
    """Get flower product by ID."""
    result = await session.execute(
        select(FlowerProduct).where(FlowerProduct.id == product_id)
    )
    return result.scalar_one_or_none()


async def add_flower_product_to_cart(
    session, user_id: int, product_id: int, title: str, price: int, quantity: int = 1
) -> CartItem:
    """Add flower product to cart. If exists, increase quantity."""
    result = await session.execute(
        select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.item_type == "flower_product",
            CartItem.item_id == product_id,
        )
    )
    item = result.scalar_one_or_none()
    if item:
        item.quantity += quantity
        await session.flush()
        await session.refresh(item)
        return item
    item = CartItem(
        user_id=user_id,
        item_type="flower_product",
        item_id=product_id,
        title=title,
        quantity=quantity,
        price=price,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return item


async def get_flower_cart_items(session, user_id: int) -> list[CartItem]:
    """Get cart items that belong to the flower cart (products + services)."""
    result = await session.execute(
        select(CartItem)
        .where(
            CartItem.user_id == user_id,
            CartItem.item_type.in_(["flower_product", "flower_service"]),
        )
        .order_by(CartItem.id)
    )
    return list(result.scalars().all())


# -----------------------------------------------------------------------------
# Cart (CartItem with user_id)
# -----------------------------------------------------------------------------


async def get_cart_items(session, user_id: int) -> list[CartItem]:
    """Get all cart items for user."""
    result = await session.execute(
        select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.id)
    )
    return list(result.scalars().all())


async def add_service_to_cart(
    session, user_id: int, service_id: int, title: str, price: int, quantity: int = 1
) -> CartItem:
    """Add service to cart. If exists, increase quantity."""
    result = await session.execute(
        select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.item_type == "service",
            CartItem.item_id == service_id,
        )
    )
    item = result.scalar_one_or_none()
    if item:
        item.quantity += quantity
        await session.flush()
        await session.refresh(item)
        return item
    item = CartItem(
        user_id=user_id,
        item_type="service",
        item_id=service_id,
        title=title,
        quantity=quantity,
        price=price,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return item


async def add_flower_to_cart(
    session, user_id: int, flower_id: int, title: str, price: int, quantity: int = 1
) -> CartItem:
    """Add flower to cart. If exists, increase quantity."""
    result = await session.execute(
        select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.item_type == "flower",
            CartItem.item_id == flower_id,
        )
    )
    item = result.scalar_one_or_none()
    if item:
        item.quantity += quantity
        await session.flush()
        await session.refresh(item)
        return item
    item = CartItem(
        user_id=user_id,
        item_type="flower",
        item_id=flower_id,
        title=title,
        quantity=quantity,
        price=price,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return item


async def remove_cart_item(session, item_id: int, user_id: int) -> bool:
    """Remove cart item. Returns True if removed."""
    result = await session.execute(
        select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if item:
        await session.delete(item)
        await session.flush()
        return True
    return False


async def clear_cart(session, user_id: int) -> None:
    """Remove all cart items for user."""
    await session.execute(delete(CartItem).where(CartItem.user_id == user_id))
    await session.flush()


async def clear_flower_cart(session, user_id: int) -> None:
    """Remove flower cart items (products + services) for user."""
    await session.execute(
        delete(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.item_type.in_(["flower_product", "flower_service"]),
        )
    )
    await session.flush()


async def add_flower_service_to_cart(
    session, user_id: int, service_id: int, title: str, price: int, quantity: int = 1
) -> CartItem:
    """Add a flower-category service to the flower cart. If exists, increase quantity."""
    result = await session.execute(
        select(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.item_type == "flower_service",
            CartItem.item_id == service_id,
        )
    )
    item = result.scalar_one_or_none()
    if item:
        item.quantity += quantity
        await session.flush()
        await session.refresh(item)
        return item
    item = CartItem(
        user_id=user_id,
        item_type="flower_service",
        item_id=service_id,
        title=title,
        quantity=quantity,
        price=price,
    )
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return item


# -----------------------------------------------------------------------------
# Regions, Districts, Cemeteries
# -----------------------------------------------------------------------------


async def get_regions(session) -> list[Region]:
    """Get all regions."""
    result = await session.execute(select(Region).order_by(Region.id))
    return list(result.scalars().all())


async def get_districts_by_region(session, region_id: int) -> list[District]:
    """Get districts for a region."""
    result = await session.execute(
        select(District).where(District.region_id == region_id).order_by(District.id)
    )
    return list(result.scalars().all())


async def get_cemeteries_by_district(session, district_id: int) -> list[Cemetery]:
    """Get cemeteries for a district."""
    result = await session.execute(
        select(Cemetery)
        .where(Cemetery.district_id == district_id)
        .order_by(Cemetery.id)
    )
    return list(result.scalars().all())


async def get_region_by_id(session, region_id: int) -> Region | None:
    result = await session.execute(select(Region).where(Region.id == region_id))
    return result.scalar_one_or_none()


async def get_district_by_id(session, district_id: int) -> District | None:
    result = await session.execute(select(District).where(District.id == district_id))
    return result.scalar_one_or_none()


async def get_cemetery_by_id(session, cemetery_id: int) -> Cemetery | None:
    result = await session.execute(select(Cemetery).where(Cemetery.id == cemetery_id))
    return result.scalar_one_or_none()


# -----------------------------------------------------------------------------
# Orders
# -----------------------------------------------------------------------------


async def create_order_from_service(
    session,
    user_id: int,
    service_id: int,
    service_title: str,
    service_price: int,
    *,
    full_name: str,
    phone_number: str,
    region_id: int | None = None,
    district_id: int | None = None,
    cemetery_id: int | None = None,
    deceased_full_name: str | None = None,
    birth_year: int | None = None,
    death_year: int | None = None,
    comment: str | None = None,
) -> Order:
    """Create order with single service (no cart)."""
    order = Order(
        user_id=user_id,
        full_name=full_name,
        phone_number=phone_number,
        region_id=region_id,
        district_id=district_id,
        cemetery_id=cemetery_id,
        deceased_full_name=deceased_full_name,
        birth_year=birth_year,
        death_year=death_year,
        comment=comment,
        total_price=service_price,
        status=ORDER_STATUS_NEW,
    )
    session.add(order)
    await session.flush()
    oi = OrderItem(
        order_id=order.id,
        item_type="service",
        item_id=service_id,
        title=service_title,
        quantity=1,
        price=service_price,
    )
    session.add(oi)
    await session.flush()
    await session.refresh(order)
    return order


async def create_order_from_flower(
    session,
    user_id: int,
    flower_id: int,
    flower_title: str,
    flower_price: int,
    *,
    full_name: str,
    phone_number: str,
) -> Order:
    """Create order with single flower (no cart). Same pattern as create_order_from_service."""
    order = Order(
        user_id=user_id,
        full_name=full_name,
        phone_number=phone_number,
        total_price=flower_price,
        status=ORDER_STATUS_NEW,
    )
    session.add(order)
    await session.flush()
    oi = OrderItem(
        order_id=order.id,
        item_type="flower",
        item_id=flower_id,
        title=flower_title,
        quantity=1,
        price=flower_price,
    )
    session.add(oi)
    await session.flush()
    await session.refresh(order)
    return order


async def create_order_from_cart(
    session,
    user_id: int,
    cart_items: list[CartItem],
    *,
    full_name: str,
    phone_number: str,
    region_id: int | None = None,
    district_id: int | None = None,
    cemetery_id: int | None = None,
    deceased_full_name: str | None = None,
    birth_year: int | None = None,
    death_year: int | None = None,
    comment: str | None = None,
) -> Order | None:
    """Create order from cart items. Clears cart. Returns order or None if cart empty."""
    if not cart_items:
        return None
    total = sum(item.quantity * item.price for item in cart_items)
    order = Order(
        user_id=user_id,
        full_name=full_name,
        phone_number=phone_number,
        region_id=region_id,
        district_id=district_id,
        cemetery_id=cemetery_id,
        deceased_full_name=deceased_full_name,
        birth_year=birth_year,
        death_year=death_year,
        comment=comment,
        total_price=total,
        status=ORDER_STATUS_NEW,
    )
    session.add(order)
    await session.flush()
    for item in cart_items:
        oi = OrderItem(
            order_id=order.id,
            item_type=item.item_type,
            item_id=item.item_id,
            title=item.title,
            quantity=item.quantity,
            price=item.price,
        )
        session.add(oi)
    await session.execute(delete(CartItem).where(CartItem.user_id == user_id))
    await session.flush()
    await session.refresh(order)
    return order


async def create_flower_order_from_cart(
    session,
    user_id: int,
    cart_items: list[CartItem],
    *,
    first_name: str,
    last_name: str,
    birth_year: int | None = None,
    death_year: int | None = None,
) -> Order | None:
    """Create order from flower cart items. Clears flower cart. Returns order or None."""
    if not cart_items:
        return None
    total = sum(item.quantity * item.price for item in cart_items)
    full_name = f"{first_name} {last_name}".strip()
    order = Order(
        user_id=user_id,
        full_name=full_name,
        phone_number="",
        first_name=first_name,
        last_name=last_name,
        birth_year=birth_year,
        death_year=death_year,
        total_price=total,
        status=ORDER_STATUS_NEW,
    )
    session.add(order)
    await session.flush()
    for item in cart_items:
        oi = OrderItem(
            order_id=order.id,
            item_type=item.item_type,
            item_id=item.item_id,
            title=item.title,
            quantity=item.quantity,
            price=item.price,
        )
        session.add(oi)
    await session.execute(
        delete(CartItem).where(
            CartItem.user_id == user_id,
            CartItem.item_type.in_(["flower_product", "flower_service"]),
        )
    )
    await session.flush()
    await session.refresh(order)
    return order


async def get_orders_by_user(session, user_id: int) -> list[Order]:
    """Get all orders for user, newest first."""
    result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.region),
            selectinload(Order.district),
            selectinload(Order.cemetery),
        )
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
    )
    return list(result.scalars().all())


async def get_order_by_id(session, order_id: int) -> Order | None:
    """Get order by ID with items and location."""
    result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.user),
            selectinload(Order.region),
            selectinload(Order.district),
            selectinload(Order.cemetery),
        )
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def update_order_receipt(
    session, order_id: int, receipt_file_id: str, payment_method: str
) -> Order | None:
    """Update order with receipt and set status to payment_review."""
    order = await get_order_by_id(session, order_id)
    if order is None:
        return None
    order.receipt_file_id = receipt_file_id
    order.payment_method = payment_method
    order.status = ORDER_STATUS_PAYMENT_REVIEW
    await session.flush()
    await session.refresh(order)
    return order


async def update_order_status(session, order_id: int, status: str) -> Order | None:
    """Update order status. Returns order or None."""
    order = await get_order_by_id(session, order_id)
    if order is None:
        return None
    order.status = status
    await session.flush()
    await session.refresh(order)
    return order


# -----------------------------------------------------------------------------
# Support
# -----------------------------------------------------------------------------


async def create_support_message(
    session, user_id: int, text: str
) -> SupportMessage:
    """Create a support message record."""
    msg = SupportMessage(user_id=user_id, text=text)
    session.add(msg)
    await session.flush()
    await session.refresh(msg)
    return msg


async def get_completed_orders_by_user(session, user_id: int) -> list[Order]:
    """Return orders with status 'completed' for a user."""
    stmt = (
        select(Order)
        .where(Order.user_id == user_id, Order.status == "completed")
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_rating_for_order(session, order_id: int) -> Rating | None:
    """Return existing rating for an order, or None."""
    stmt = select(Rating).where(Rating.order_id == order_id)
    result = await session.execute(stmt)
    return result.scalars().first()


async def create_rating(session, user_id: int, order_id: int, value: str) -> Rating:
    """Create a new rating record."""
    rating = Rating(user_id=user_id, order_id=order_id, value=value)
    session.add(rating)
    await session.flush()
    await session.refresh(rating)
    return rating


async def update_rating_comment(session, rating_id: int, comment: str) -> Rating | None:
    """Add comment to existing rating."""
    stmt = select(Rating).where(Rating.id == rating_id)
    result = await session.execute(stmt)
    rating = result.scalars().first()
    if rating:
        rating.comment = comment
        await session.flush()
    return rating


async def get_or_create_cart(session, user_id: int) -> Cart:
    """Return a Cart wrapper with all CartItem rows for the given user."""
    stmt = select(CartItem).where(CartItem.user_id == user_id)
    result = await session.execute(stmt)
    items = list(result.scalars().all())
    return Cart(user_id=user_id, items=items)


async def create_complaint(
    session, user_id: int, text: str
) -> SupportMessage:
    """Create a complaint record (stored as SupportMessage)."""
    msg = SupportMessage(user_id=user_id, text=text)
    session.add(msg)
    await session.flush()
    await session.refresh(msg)
    return msg


# -----------------------------------------------------------------------------
# Order Assignment and Photo Upload
# -----------------------------------------------------------------------------


async def assign_order(
    session, order_id: int, telegram_id: int, username: str | None = None
) -> Order | None:
    """Assign an order to a worker."""
    from datetime import datetime
    stmt = select(Order).where(Order.id == order_id)
    result = await session.execute(stmt)
    order = result.scalars().first()
    if order:
        order.assigned_telegram_id = telegram_id
        order.assigned_username = username
        order.assigned_at = datetime.utcnow()
        order.status = "in_progress"
        await session.flush()
    return order


async def upload_order_photo(
    session, order_id: int, photo_file_id: str
) -> tuple[Order | None, int]:
    """Upload a photo to order. Returns (order, photo_number 1 or 2)."""
    from datetime import datetime
    stmt = select(Order).where(Order.id == order_id)
    result = await session.execute(stmt)
    order = result.scalars().first()
    if not order:
        return None, 0

    if not order.photo1_file_id:
        order.photo1_file_id = photo_file_id
        await session.flush()
        return order, 1
    elif not order.photo2_file_id:
        order.photo2_file_id = photo_file_id
        order.photos_uploaded_at = datetime.utcnow()
        order.status = "completed"
        await session.flush()
        return order, 2
    return order, 0  # Both photos already uploaded


async def get_orders_needing_reminder(session, hours: int = 2) -> list[Order]:
    """Get orders assigned more than N hours ago without reminder sent.

    Default: 2 hours (for 3-hour deadline, reminder at 2h = 1h left).
    """
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    stmt = (
        select(Order)
        .where(
            Order.assigned_at != None,
            Order.assigned_at <= cutoff,
            Order.reminder_sent == False,
            Order.photo2_file_id == None,
            Order.status.in_(["paid", "in_progress"]),
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_reminder_sent(session, order_id: int) -> None:
    """Mark reminder as sent for an order."""
    stmt = select(Order).where(Order.id == order_id)
    result = await session.execute(stmt)
    order = result.scalars().first()
    if order:
        order.reminder_sent = True
        await session.flush()


async def get_overdue_orders(session, hours: int = 3) -> list[Order]:
    """Get orders assigned more than N hours ago without 2 photos.

    Default: 3 hours deadline.
    """
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    stmt = (
        select(Order)
        .where(
            Order.assigned_at != None,
            Order.assigned_at <= cutoff,
            Order.photo2_file_id == None,
            Order.status.in_(["paid", "in_progress"]),
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def update_order_grave(session, order_id: int, grave_id: int) -> None:
    """Update order with grave_id."""
    stmt = select(Order).where(Order.id == order_id)
    result = await session.execute(stmt)
    order = result.scalars().first()
    if order:
        order.grave_id = grave_id
        await session.flush()
