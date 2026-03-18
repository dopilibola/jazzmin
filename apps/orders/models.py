from django.db import models
from apps.catalog.models import Service, Flower


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    user_telegram_id = models.BigIntegerField()
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    service = models.ForeignKey(
        Service, on_delete=models.PROTECT, related_name='orders',
    )
    flower = models.ForeignKey(
        Flower, on_delete=models.PROTECT, related_name='orders',
        blank=True, null=True,
    )
    cemetery_name = models.CharField(max_length=255)
    grave_owner_name = models.CharField(max_length=255)
    order_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING,
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"Order #{self.pk} — {self.full_name} ({self.get_status_display()})"
