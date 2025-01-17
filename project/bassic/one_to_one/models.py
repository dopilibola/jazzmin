from django.db import models


# o'lgan odamni ma'lumotlari 
class Infodata(models.Model):
    idname = models.CharField(max_length=20, blank=True)
    malumotnoma_num = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=50, blank=True)
    vafot_etgan_sana = models.CharField(max_length=20, blank=True)
    dalolatnoma_sanasi = models.CharField(max_length=20, blank=True)
    dalolatnoma_raqami =models.CharField(max_length=20, blank=True)
    olim_sababi = models.CharField(max_length=20, blank=True)
    qayt_qilingan_FHDY_bolim = models.CharField(max_length=20, blank=True)
    tugilgan_vaqti = models.CharField(max_length=20, blank=True)
    yosh = models.CharField(max_length=20, blank=True)
    vafot_etgan_joy = models.CharField(max_length=20, blank=True)
    malumot_berilgan_sana = models.CharField(max_length=20, blank=True)
    vafot_etgan_shaxsning_JSHIR = models.CharField(max_length=20, blank=True)
    tibbiyot_muassasasi = models.CharField(max_length=20, blank=True)
    royhatga_olingan_vaqt = models.CharField(max_length=20, blank=True)
    
    karta_number = models.CharField(max_length=20, blank=True)
    qator =  models.CharField(max_length=20, blank=True)
    qabr_soni = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return f'{self.full_name} {self.vafot_etgan_sana} - {self.vafot_etgan_shaxsning_JSHIR}'

# go'rkov uchun qabirni topish uchun applar

class Qabriston(models.Model):
    idname = models.CharField(max_length=20, blank=True)
    karta_number = models.CharField(max_length=20, blank=True)
    qator =  models.CharField(max_length=20, blank=True)
    qabr_soni = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f'{self.karta_number} - {self.qator} {self.qabr_soni}'



