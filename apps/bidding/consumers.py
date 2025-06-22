# auction_web/apps/bidding/consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db import transaction
from asgiref.sync import sync_to_async
from decimal import Decimal
from django.core.serializers.json import DjangoJSONEncoder

# Import các models cần thiết
from apps.items.models import Item
from apps.bidding.models import Bid, Escrow
from apps.auth_users.models import User # <-- SỬA LẠI, DÙNG USER MODEL

class BidConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.item_id = self.scope['url_route']['kwargs']['item_id']
        self.item_group_name = f'item_bid_{self.item_id}'
        # Lấy thông tin user từ scope
        self.user = self.scope.get('user')
        
        await self.channel_layer.group_add(self.item_group_name, self.channel_name)
        await self.accept()
        print(f"WebSocket connected for item {self.item_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.item_group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Nhận message từ WebSocket khi người dùng đặt giá.
        """
        if not self.user or not self.user.is_authenticated:
            await self.send(text_data=json.dumps({'error': 'Bạn cần đăng nhập để đấu giá.'}))
            return

        data = json.loads(text_data)
        bid_amount_str = data.get('bid_amount')

        if not bid_amount_str:
            await self.send(text_data=json.dumps({'error': 'Giá không hợp lệ.'}))
            return
            
        try:
            bid_amount = Decimal(bid_amount_str)
        except (ValueError, TypeError):
            await self.send(text_data=json.dumps({'error': 'Số tiền không hợp lệ.'}))
            return

        try:
            # Gọi hàm xử lý logic đấu giá
            event_data, error_data = await self._process_bid(self.user, self.item_id, bid_amount)

            # Nếu có lỗi, chỉ gửi cho người dùng hiện tại
            if error_data:
                await self.send(text_data=json.dumps(error_data))
                return

            # Nếu thành công, gửi thông tin cập nhật đến cả group
            await self.channel_layer.group_send(
                self.item_group_name,
                event_data
            )
        except Exception as e:
            await self.send(text_data=json.dumps({'error': f'Đã xảy ra lỗi hệ thống: {str(e)}'}))

    @sync_to_async
    @transaction.atomic
    def _process_bid(self, user, item_id, bid_amount):
        """
        Hàm xử lý nghiệp vụ đặt giá - PHIÊN BẢN CÓ THÊM LOG GỠ LỖI.
        """
        from apps.auth_users.models import User

        # --- BẮT ĐẦU GỠ LỖI ---
        print("\n" + "="*50)
        print(f"[DEBUG] Bắt đầu xử lý bid cho user: {user.username}, Item ID: {item_id}")
        
        item = Item.objects.select_for_update().get(id=item_id)
        bidder = User.objects.select_for_update().get(pk=user.pk)

        print(f"[DEBUG] Giá khởi điểm của sản phẩm: {item.starting_price}")
        print(f"[DEBUG] Giá hiện tại của sản phẩm: {item.current_price}")
        print(f"[DEBUG] Số dư của user '{bidder.username}' từ DB: {bidder.balance} (Kiểu dữ liệu: {type(bidder.balance)})")
        print(f"[DEBUG] Số tiền bid nhận từ client: {bid_amount} (Kiểu dữ liệu: {type(bid_amount)})")
        # --- KẾT THÚC GỠ LỖI ---

        # 1. Kiểm tra các điều kiện hợp lệ
        if not item.is_active:
            return None, {'error': 'Phiên đấu giá cho sản phẩm này đã kết thúc.'}
        
        # KIỂM TRA SỐ DƯ TRỰC TIẾP TRÊN USER MODEL
        if bidder.balance < bid_amount:
            shortfall = bid_amount - bidder.balance
            # Lưu vào session nếu cần thiết cho việc chuyển hướng
            # self.scope['session']['shortfall_amount'] = float(shortfall)
            # self.scope['session'].save()
            return None, {
                'error': 'Số dư không đủ. Vui lòng nạp thêm tiền.',
                'error_code': 'INSUFFICIENT_FUNDS',
                'redirect_url': '/wallet/', # Điều chỉnh URL nếu cần
            }
            
        if bid_amount <= item.current_price:
            return None, {'error': f'Giá của bạn phải cao hơn {item.current_price:,.0f} đ.'}

        # 2. Hoàn trả tiền cho người giữ giá cao trước đó
        previous_escrow = Escrow.objects.filter(item=item, status=Escrow.Status.HELD).first()
        if previous_escrow:
            # Lấy user cũ và cộng tiền lại vào balance của họ
            previous_bidder = User.objects.select_for_update().get(pk=previous_escrow.user.pk)
            previous_bidder.balance += previous_escrow.amount
            previous_bidder.save(update_fields=['balance'])
            
            previous_escrow.status = Escrow.Status.REFUNDED
            previous_escrow.save()

        # 3. Trừ tiền từ balance của người đặt giá hiện tại
        bidder.balance -= bid_amount
        bidder.save(update_fields=['balance'])

        # 4. Tạo bản ghi Escrow mới để giữ tiền
        Escrow.objects.create(
            item=item,
            user=user,
            amount=bid_amount,
            status=Escrow.Status.HELD
        )

        # 5. Tạo Bid và cập nhật Item
        new_bid = Bid.objects.create(item=item, user=user, bid_amount=bid_amount)
        item.current_price = bid_amount
        item.current_highest_bid = new_bid
        item.save()

        # 6. Chuẩn bị dữ liệu để gửi đi
        bid_history_qs = Bid.objects.filter(item=item).order_by('-timestamp').select_related('user')
        bid_history = [{
            'bidder_name': bid.user.username,
            'bid_amount': bid.bid_amount,
            'timestamp': bid.timestamp
        } for bid in bid_history_qs]

        event_data = {
            'type': 'bid_update', # Phải trùng với tên hàm xử lý (bid_update)
            'item_details': {
                'id': item.id,
                'current_price': item.current_price,
                'total_bids': bid_history_qs.count()
            },
            'bid_history': json.loads(json.dumps(bid_history, cls=DjangoJSONEncoder)),
            'new_highest_bid': {
                'bidder_name': user.username,
                'bid_amount': new_bid.bid_amount
            },
            'bidder_info': { 'id': user.id, 'username': user.username },
            'action_info': f'{user.username} vừa đặt giá mới!'
        }
        return event_data, None

    # Các hàm có sẵn của bạn để nhận và gửi thông điệp
    async def bid_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'bid_update',
            'item_details': event.get('item_details'),
            'bid_history': event.get('bid_history'),
            'new_highest_bid': event.get('new_highest_bid'),
            'bidder_info': event.get('bidder_info'),
            'action_info': event.get('action_info'),
        }))

    async def auction_ended_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'auction_ended_update',
            'item_details': event.get('item_details'),
            'winner_info': event.get('winner_info'),
            'message': event.get('message'),
        }))

# Lớp HomeBidConsumer của bạn (giữ nguyên)
class HomeBidConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "homepage_items"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        print("WebSocket connected for home")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def bid_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'bid_update',
            'item_details': event.get('item_details'),
        }))