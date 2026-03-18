from apps.orders.models import Order


def create_order(**kwargs):
    order = Order.objects.create(**kwargs)
    return Order.objects.select_related('service', 'flower').get(pk=order.pk)
