from django.db import models
from django.conf import settings



# Create your models here.
class Item(models.Model):
    item_id = models.AutoField(primary_key=True)
    seller_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image_url = models.CharField(max_length=255, blank=True, null=True)
    starting_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=10,
        choices=[('ongoing', 'Ongoing'), ('completed', 'Completed'), ('canceled', 'Canceled')],
        default='ongoing'
    )

    class Meta:
        db_table = 'items'

    def __str__(self):
        return self.name
