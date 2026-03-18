# Flower Feature Module

Modular flower services for the grave care Telegram bot.

## Overview

- **Flower Categories**: Two categories (planted around grave / placed on grave)
- **Flower Products**: Image, name, description, price, Add to Cart
- **Cart**: Flower products, quantity, price, remove, clear, confirm
- **Order Form**: First name, last name, birth year, death year
- **Payment**: Upload receipt screenshot → status = payment_review
- **Order History**: My Orders with status

## Database Models

- **FlowerCategory**: id, name_en, name_ru, name_uz
- **FlowerProduct**: id, category_id, name, description, price, image_file_id
- **CartItem**: Uses item_type="flower_product", item_id=product_id
- **Order**: first_name, last_name, birth_year, death_year, total_price, receipt_file_id, status
- **OrderItem**: item_type="flower_product", item_id=product_id, title, quantity, price

## User Flow

1. **Flowers** (main menu) → Flower categories
2. Select category → Product list with Add to Cart
3. Add items → **Cart** button → Flower cart
4. **Confirm Order** → Form (first name, last name, birth year, death year)
5. **Proceed to Payment** → Upload receipt screenshot
6. Receipt saved, status = payment_review
7. **My Orders** → View order history

## Callback Data Prefixes

- `flcat:` — Flower category (menu, category id)
- `flprod:add:` — Add flower product to cart
- `flcart:` — Flower cart (view, remove, clear, confirm)
- `flord:` — Flower order (proceed, cancel)

## Files

- `bot/handlers/flowers.py` — All flower handlers
- `bot/database/models.py` — FlowerCategory, FlowerProduct
- `bot/database/queries.py` — Flower CRUD, create_flower_order_from_cart
- `bot/database/seed.py` — seed_flower_categories_and_products
- `bot/keyboards/inline.py` — flower_categories_inline, flower_products_inline, flower_cart_inline, flower_confirm_order_inline
- `bot/states/forms.py` — FlowerCheckoutState, FlowerPaymentState
