from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

# Import các model liên quan
from apps.items.models import Item
from apps.bidding.models import Escrow
# Import model WalletTransaction từ app wallet
from apps.wallet.models import WalletTransaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Finds finished auctions and creates a pending WalletTransaction for the winner.'

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        # Lấy các phiên đấu giá đã kết thúc và còn active
        finished_auctions = Item.objects.select_for_update().filter(
            end_time__lte=now,
            is_active=True
        )

        if not finished_auctions.exists():
            self.stdout.write(self.style.SUCCESS('No finished auctions to process.'))
            return

        self.stdout.write(f'Found {finished_auctions.count()} finished auctions to process...')

        for item in finished_auctions:
            winner_bid = item.current_highest_bid

            if winner_bid:
                winner = winner_bid.user

                # Tìm bản ghi escrow đang HELD của người thắng
                winning_escrow = Escrow.objects.filter(
                    item=item,
                    user=winner,
                    status=Escrow.Status.HELD
                ).first()

                if winning_escrow:
                    # TẠO BẢN GHI WALLETTRANSACTION ĐẠI DIỆN CHO THỎA THUẬN
                    WalletTransaction.objects.create(
                        owner=winner,
                        seller=item.seller,
                        transaction_type='AUCTION_SALE',
                        amount=winner_bid.bid_amount,  # Lưu tổng giá trị thắng
                        status='PENDING_PAYMENT',
                        item=item,
                        escrow=winning_escrow,
                        payment_due_date=now + timedelta(days=3), # Hạn thanh toán là 3 ngày
                        description=f'Thỏa thuận thanh toán cho sản phẩm "{item.name}"'
                    )

                    # Đóng phiên đấu giá
                    item.is_active = False
                    item.save()

                    self.stdout.write(self.style.SUCCESS(
                        f'Created pending transaction for item "{item.name}". Winner: {winner.username}'
                    ))
                else:
                    logger.error(f'Winning escrow record not found for item {item.id}. Cannot create transaction.')
                    item.is_active = False
                    item.save()
            else:
                # Không có ai đấu giá, chỉ cần đóng lại
                item.is_active = False
                item.save()