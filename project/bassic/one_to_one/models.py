from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator

# o'lgan odamni ma'lumotlari 
class Infodata(models.Model):
    idname = models.CharField(max_length=20, blank=True)
    malumotnoma_num = models.CharField(max_length=20, blank=True) 
    ism_familiyasi_marhum = models.CharField(max_length=20, blank=True) 
    qarindoshligi = models.CharField(max_length=50, blank=True)  #tanlaydigan tugmasi bo'lishi kerak 
    ism_familiyasi_ishonchlivakil = models.CharField(max_length=20, blank=True) 
    telefon_numeri = models.CharField(max_length=20, blank=True) #faqat nummer bo'lishi kerak 
    JSHSHIR_ishonch_vakil = models.CharField(max_length=20, blank=True) #14talik raqam bo'lishi kerak 
    # Qabriston ma'lumotlari 
    # viloyat =models.CharField(max_length=20, blank=True)
    # tuman  = models.CharField(max_length=20, blank=True)
    # mahalla = models.CharField(max_length=20, blank=True)
    # JSHSHIR_olgan = models.CharField(max_length=20, blank=True)
    # gorkov_bilanmi = models.CharField(max_length=20, blank=True) #tugmali 
    # qabriston_joy = models.CharField(max_length=20, blank=True) #tugmali agar bosilsa keyingisiga otsin
    # # Ustiga ko'mish 
    # marhumning_qarindoshligi = models.CharField(max_length=20, blank=True)
    # ism_familiyasi = models.CharField(max_length=20, blank=True) 
    # tibbiyot_muassasasi = models.CharField(max_length=20, blank=True)
    # royhatga_olingan_vaqt = models.CharField(max_length=20, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'{self.malumotnoma_num} {self.ism_familiyasi_ishonchlivakil} -'

# go'rkov uchun qabirni topish uchun applar
class Qabriston(models.Model):
    idname = models.CharField(max_length=20, blank=True)
    karta_number = models.CharField(max_length=20, blank=True)
    qator =  models.CharField(max_length=20, blank=True)
    # qabr_son = models.CharField(max_length=20, blank=True)  # nomni 'qabr_soni' dan 'qabr_son'ga o'zgartirdim
    qabr_soni = models.CharField(max_length=20, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'{self.karta_number} - {self.qator} {self.qabr_soni}'  # 'qabr_soni' ni 'qabr_son' ga o'zgartirdim


class Image(models.Model):
    image = models.ImageField(upload_to='hujjat/')  # Rasmni 'images/' papkaga saqlash
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return self.description

