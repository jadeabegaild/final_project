from django.db import models

class Harvest(models.Model):
    date = models.DateField()
    kilograms = models.FloatField()

    def __str__(self):
        return f"{self.date} - {self.kilograms} kg"
