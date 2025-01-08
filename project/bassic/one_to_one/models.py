from django.db import models
import datetime

# o'lgan odamni ma'lumotlari 
class Infodata(models.Model):
    first_name = models.CharField(max_length=20, blank=True)
    last_name = models.CharField(max_length=20, blank=True)
    idname = models.CharField(max_length=20, blank=True)
    passportdata = models.CharField(max_length=20, blank=True)
    birthday = models.CharField(max_length=20, blank=True)
    data = models.DateField(default=datetime.datetime.today)

    def __str__(self):
        return f'{self.first_name} {self.last_name} - {self.passportdata}'




# o'lgan odamni qarindoshini ma'lumotlari 
# class Infodata2(models.Model):
#     first_name = models.CharField(max_length=20, blank=True)
#     last_name = models.CharField(max_length=20, blank=True)
#     phone = models.CharField(max_length=20, blank=True)
#     Cousins = models.CharField(max_length=20, blank=True)
    

# Create your models here.
