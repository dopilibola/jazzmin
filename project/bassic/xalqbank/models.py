from django.db import models

# o'lgan odamni ma'lumotlari
class Desnoot(models.Model):
    idname = models.CharField(max_length=20, blank=True)
    surname = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=20, blank=True)
    patronymic = models.CharField(max_length=20, blank=True)
    data_of_birth = models.DateField(max_length=20, blank=True) #data filter 
    cart_number = models.CharField(max_length=20, blank=True)  #AD 7ta raqam number filter
    personal_number = models.CharField(max_length=20, blank=True) #number 14  JSSHER 
    mahalla_id = models.CharField(max_length=20, blank=True)  #mahalla berdigan qog'oz id 
    mahalla_name = models.CharField(max_length=20, blank=True) # mahallani nomi 

    def __str__(self):
        return f'{self.name} {self.mahalla_id} -{self.personal_number}'
    
    #kafilni ma'lumotlari va cart numberi  
class Guardianship(models.Model):
    idname = models.CharField(max_length=20, blank=True)
    surname = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=20, blank=True)
    patronymic = models.CharField(max_length=20, blank=True)
    data_of_birth = models.CharField(max_length=20, blank=True) #data filter 
    cart_number = models.CharField(max_length=20, blank=True)  #AD 7ta raqam number filter
    personal_number = models.CharField(max_length=20, blank=True) #number 14  JSSHER 
    cart_number_p = models.CharField(max_length=20, blank=True) # 16 number filter
    
    def __str__(self):
        return f'{self.name} {self.cart_number} {self.cart_number_p} -{self.personal_number}'