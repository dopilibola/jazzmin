from apps.catalog.models import Service, Flower


def get_active_services():
    return list(Service.objects.filter(is_active=True).order_by('name'))


def get_active_flowers():
    return list(Flower.objects.filter(is_active=True).order_by('name'))


def get_service_by_id(service_id):
    try:
        return Service.objects.get(id=service_id)
    except Service.DoesNotExist:
        return None


def get_flower_by_id(flower_id):
    try:
        return Flower.objects.get(id=flower_id)
    except Flower.DoesNotExist:
        return None
