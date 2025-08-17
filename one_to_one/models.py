from django.db import models


# o'lgan odamni ma'lumotlari 
class Infodata(models.Model):
    idname = models.CharField(max_length=20, blank=True)
    ism_familiyasi_marhum = models.CharField(max_length=20, blank=True) 
    yoshi = models.CharField(max_length=20, blank=True) 
    karta_number = models.CharField(max_length=20, blank=True)
    qabr_soni = models.CharField(max_length=20, blank=True)
    royhatga_olingan_joy = models.CharField(max_length=20, blank=True)
    malumotnoma_num = models.CharField(max_length=20, blank=True) 
    uy_manzili =  models.CharField(max_length=20, blank=True)
    olim_sababi =  models.CharField(max_length=20, blank=True)
    qarindoshligi = models.CharField(max_length=50, blank=True)  #tanlaydigan tugmasi bo'lishi kerak 
    ism_familiyasi_ishonchlivakil = models.CharField(max_length=20, blank=True) 
    telefon_numeri = models.CharField(max_length=20, blank=True) #faqat nummer bo'lishi kerak 
    gorkov_bilanmi = models.CharField(max_length=20, blank=True) #tugmali 
    # created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    

    def __str__(self):
        return f'{self.malumotnoma_num} {self.ism_familiyasi_ishonchlivakil} -'

# go'rkov uchun qabirni topish uchun applar
class Qabriston(models.Model):
    idname = models.CharField(max_length=20, blank=True)
    karta_number = models.CharField(max_length=20, blank=True)
    qator =  models.CharField(max_length=20, blank=True)
    # qabr_son = models.CharField(max_length=20, blank=True)  # nomni 'qabr_soni' dan 'qabr_son'ga o'zgartirdim
    qabr_soni = models.CharField(max_length=20, blank=True)
    # created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f'{self.karta_number} - {self.qator} {self.qabr_soni}'  # 'qabr_soni' ni 'qabr_son' ga o'zgartirdim


class Image(models.Model):
    image = models.ImageField(upload_to='media/hujjat/')  # Rasmni 'images/' papkaga saqlash
    malumotnoma_nomeri = models.CharField(max_length=255, blank=True)
    # created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return self.malumotnoma_nomeri
