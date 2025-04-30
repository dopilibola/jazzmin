from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save

# Profile modelini to'g'rilaymiz
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, default='Unknown')
    job = models.CharField(max_length=255, default='Unemployed')
    image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    date_modified = models.DateTimeField(auto_now=True)  # fixing typo in field name
    phone = models.CharField(max_length=200, blank=True)
    address1 = models.CharField(max_length=200, blank=True)
    address2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=200, blank=True)
    zipcode = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    old_cart = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.user.username


# Signal to create Profile when user is created
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

post_save.connect(create_profile, sender=User)



# vil tuman shahar 
