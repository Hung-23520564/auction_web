from django.db import models
from django.contrib.auth.models import User
from apps.auth_users.models import User
from apps.items.models import Item
from django.conf import settings

class Bid(models.Model):
    bid_id = models.AutoField(primary_key=True)
    item_id = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='bids')  # Sản phẩm được đấu giá
    user_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Người đặt giá
    bid_amount = models.DecimalField(max_digits=25, decimal_places=0)  # Giá đấu thầu
    bid_time = models.DateTimeField(auto_now_add=True)  # Thời gian đặt giá

class Escrow(models.Model):
    """
    Model để lưu trữ các khoản tiền đặt cọc (escrow) cho mỗi lần đấu giá.
    """
    class Status(models.TextChoices):
        HELD = 'HELD', 'Đang giữ'
        REFUNDED = 'REFUNDED', 'Đã hoàn trả'
        TRANSFERRED = 'TRANSFERRED', 'Đã chuyển'

    # Liên kết tới phiên đấu giá (sản phẩm)
    item = models.ForeignKey(
        Item, 
        on_delete=models.CASCADE, 
        related_name='escrows'
    )
    # Liên kết tới người dùng đặt cọc
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='escrows'
    )
    # Số tiền đã đặt cọc
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    # Trạng thái của khoản cọc
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.HELD
    )
    # Thời điểm tạo
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Cọc {self.amount} cho {self.item.name} bởi {self.user.username} - {self.get_status_display()}'

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['item', 'status']),
        ]

    def __str__(self):
        return f"Bid {self.bid_id} - {self.user_id.username} - {self.bid_amount}"
    
    class Meta:
        db_table = "bids"  # Trùng khớp với bảng trong MySQL
