from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
import logging

# Import các model liên quan
from apps.wallet.models import WalletTransaction, Wallet

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Checks for auction sales with expired payment windows and forfeits the deposit.'

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        
        # Tìm các giao dịch đấu giá đang chờ thanh toán và đã quá hạn
        expired_sales = WalletTransaction.objects.select_for_update().filter(
            transaction_type='AUCTION_SALE',
            status='PENDING_PAYMENT',
            payment_due_date__lte=now
        )

        if not expired_sales.exists():
            self.stdout.write(self.style.SUCCESS('No expired auction transactions to process.'))
            return

        self.stdout.write(f'Found {expired_sales.count()} expired auction transactions to process...')

        for sale_txn in expired_sales:
            # Lấy các đối tượng liên quan từ bản ghi giao dịch
            escrow = sale_txn.escrow
            seller = sale_txn.seller
            winner = sale_txn.owner
            
            # Đảm bảo các liên kết tồn tại
            if not all([escrow, seller, winner]):
                logger.error(f'Transaction ID {sale_txn.id} is missing linked escrow, seller, or owner. Skipping.')
                sale_txn.status = 'FAILED'
                sale_txn.description += '\nLỗi hệ thống: Thiếu thông tin liên kết.'
                sale_txn.save()
                continue

            try:
                seller_wallet = Wallet.objects.select_for_update().get(user=seller)

                # 1. Chuyển tiền cọc bị mất cho người bán
                deposit_amount = escrow.amount
                seller_wallet.balance += deposit_amount
                seller_wallet.save()

                # 2. Cập nhật trạng thái của Escrow thành đã chuyển
                escrow.status = escrow.Status.TRANSFERRED
                escrow.save()
                
                # 3. Cập nhật trạng thái của Giao dịch chính thành thất bại
                sale_txn.status = 'FAILED'
                sale_txn.description += f'\nThanh toán quá hạn. Người mua mất cọc. Tiền cọc {deposit_amount:,.0f} VNĐ đã được chuyển cho người bán.'
                sale_txn.save()
                
                # Tùy chọn: Bạn có thể thêm logic để mở lại phiên đấu giá cho sản phẩm này ở đây
                # item = sale_txn.item
                # item.is_active = True
                # ...
                
                self.stdout.write(self.style.SUCCESS(
                    f'Sale for item "{sale_txn.item.name}" (Txn ID: {sale_txn.id}) has failed. '
                    f'Deposit of {deposit_amount:,.0f} forfeited to seller {seller.username}.'
                ))

            except Wallet.DoesNotExist:
                logger.error(f'Wallet not found for seller {seller.username} on failed sale for item {sale_txn.item.id}.')
                # Cập nhật giao dịch thất bại để không xử lý lại
                sale_txn.status = 'FAILED'
                sale_txn.description += '\nLỗi hệ thống: Không tìm thấy ví của người bán.'
                sale_txn.save()