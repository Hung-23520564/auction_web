from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .serializers import Bidserializers
from apps.auth_users.models import User # HOẶC from django.conf import settings rồi dùng settings.AUTH_USER_MODEL
from .models import Bid
from apps.items.models import Item
from apps.payments.models import Transaction 
from django.utils.timezone import now # Có thể dùng timezone.now()
from rest_framework.permissions import IsAuthenticated
from decimal import Decimal, InvalidOperation
from django.db import transaction as django_db_transaction
from django.db.models import Max # Max được sử dụng trong code của bạn
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from urllib.parse import urlencode
from django.db.models import Case, When, Value 
from apps.bidding.models import Escrow

# Imports cho Django Channels
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# import logging # Nếu bạn muốn ghi log chi tiết
# logger = logging.getLogger(__name__)

# --- HÀM HELPER ĐỂ CHUẨN BỊ DỮ LIỆU CHO WEBSOCKET ---
# QUAN TRỌNG: Bạn cần tùy chỉnh các hàm này để phù hợp với cấu trúc dữ liệu
# mà JavaScript (bidding_detail.js) của bạn cần.
def get_item_details_for_socket(item_obj):
    """
    Chuẩn bị dữ liệu chi tiết item dưới dạng dictionary để gửi qua WebSocket.
    TÙY CHỈNH HÀM NÀY CHO PHÙ HỢP VỚI SERIALIZER HOẶC CẤU TRÚC DỮ LIỆU CỦA BẠN.
    """
    return {
        'item_id': item_obj.pk,
        'name': item_obj.name,
        'image_url': item_obj.image_url if item_obj.image_url else '/static/images/placeholder_item_large.png', # Ví dụ
        'seller': {'email': item_obj.seller.email} if item_obj.seller else {'email': 'Người bán ẩn danh'}, # Ví dụ
        'current_price': str(item_obj.current_price), # Đảm bảo là string
        'starting_price': str(item_obj.starting_price), # Đảm bảo là string
        'end_time': item_obj.end_time.isoformat() if item_obj.end_time else None,
        'status': item_obj.status,
        # Thêm các trường khác mà updateItemUI trong bidding_detail.js cần
    }

def get_bid_history_for_socket(item_obj, limit=10):
    """
    Chuẩn bị lịch sử đấu giá dưới dạng list của dictionaries để gửi qua WebSocket.
    TÙY CHỈNH HÀM NÀY CHO PHÙ HỢP VỚI SERIALIZER HOẶC CẤU TRÚC DỮ LIỆU CỦA BẠN.
    """
    bids_query = Bid.objects.filter(item_id=item_obj).select_related('user_id').order_by('-bid_time')[:limit]
    # Nếu Bidserializers đã có user_detail (email) thì có thể dùng:
    # return Bidserializers(bids_query, many=True).data
    # Nếu không, tạo thủ công:
    bid_history = []
    for bid in bids_query:
        bid_history.append({
            'bid_amount': str(bid.bid_amount), # Đảm bảo là string
            'user_detail': {'email': bid.user_id.email if bid.user_id else 'Người dùng ẩn danh'},
            'bid_time': bid.bid_time.isoformat(),
        })
    return bid_history

# --- HÀM TIỆN ÍCH XỬ LÝ PHIÊN ĐẤU GIÁ KẾT THÚC ---
def xu_ly_phien_dau_gia_ket_thuc(item_id):
    try:
        # Thêm select_related để tối ưu query nếu bạn truy cập seller nhiều lần
        san_pham_ket_thuc = Item.objects.select_related('seller').get(pk=item_id)
        thoi_gian_hien_tai_utc = timezone.now()

        if san_pham_ket_thuc.status == 'ongoing' and san_pham_ket_thuc.end_time <= thoi_gian_hien_tai_utc:
            # Lấy bid thắng cuộc trước khi vào transaction để tránh vấn đề nếu có race condition nhỏ
            # (dù trong trường hợp này có thể không quá nghiêm trọng)
            bid_thang_cuoc_obj = Bid.objects.filter(item_id=san_pham_ket_thuc).select_related('user_id').order_by('-bid_amount', '-bid_time').first()

            with django_db_transaction.atomic():
                san_pham_ket_thuc.status = 'completed'
                san_pham_ket_thuc.save(update_fields=['status'])

                if bid_thang_cuoc_obj:
                    giao_dich_da_ton_tai = Transaction.objects.filter(
                        item_id=san_pham_ket_thuc,
                        buyer_id=bid_thang_cuoc_obj.user_id
                    ).exists()

                    if not giao_dich_da_ton_tai:
                        nguoi_ban = san_pham_ket_thuc.seller
                        if not nguoi_ban:
                            print(f"Loi: Khong tim thay nguoi ban cho item {san_pham_ket_thuc.pk} khi tao giao dich.")
                            raise ValueError(f"Thieu nguoi ban cho san pham {san_pham_ket_thuc.pk}")

                        Transaction.objects.create(
                            item_id=san_pham_ket_thuc,
                            buyer_id=bid_thang_cuoc_obj.user_id,
                            seller_id=nguoi_ban,
                            final_price=bid_thang_cuoc_obj.bid_amount,
                            status='pending'
                        )
                        print(f"Auction for item {san_pham_ket_thuc.name} completed. Winner: {bid_thang_cuoc_obj.user_id.email}. Price: {bid_thang_cuoc_obj.bid_amount}")
                else:
                    print(f"Auction for item {san_pham_ket_thuc.name} completed. No bids placed.")

            # --- GỬI THÔNG BÁO REAL-TIME KHI PHIÊN KẾT THÚC ---
            channel_layer = get_channel_layer()
            item_group_name = f'item_bid_{san_pham_ket_thuc.pk}'
            
            winner_info = None
            if bid_thang_cuoc_obj:
                winner_info = {
                    'email': bid_thang_cuoc_obj.user_id.email,
                    'bid_amount': str(bid_thang_cuoc_obj.bid_amount)
                }
            
            # Dữ liệu item chi tiết sau khi cập nhật status
            item_details_data = get_item_details_for_socket(san_pham_ket_thuc)

            async_to_sync(channel_layer.group_send)(
                item_group_name,
                {
                    'type': 'auction_ended_update', # Consumer cần xử lý type này
                    'item_details': item_details_data, # Gửi lại toàn bộ chi tiết item đã cập nhật
                    'winner_info': winner_info,
                    'message': f"Phiên đấu giá cho '{san_pham_ket_thuc.name}' đã kết thúc."
                }
            )
            # ----------------------------------
            return True
    except Item.DoesNotExist:
        print(f"Item with ID {item_id} does not exist for processing ended auction.")
    except Exception as e:
        # Thêm log chi tiết hơn nếu cần
        print(f"Error processing ended auction for item ID {item_id}: {e}")
    return False

# Hàm làm tròn tiền
def Lamtrontien (amount):
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, TypeError):
            return Decimal('0')
    nghin = amount // 1000
    tram  = amount % 1000
    if tram >= 500 :
        return (nghin + 1) * 1000
    else:
        return nghin * 1000


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@django_db_transaction.atomic
def place_bid(request):
    user = request.user
    item_id_str = request.data.get('item_id')
    bid_amount_str = request.data.get('bid_amount')
    deposit_confirmed = request.data.get('deposit_confirmed', False)

    # --- 1. VALIDATE DỮ LIỆU ĐẦU VÀO ---
    if not item_id_str or not bid_amount_str:
        return Response({"error": "Thiếu dữ liệu đầu vào."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        item_id_int = int(item_id_str)
        bid_amount = Decimal(bid_amount_str)
        item = Item.objects.select_related('seller').select_for_update().get(pk=item_id_int)
        bidder_db = User.objects.select_for_update().get(pk=user.pk)
    except (ValueError, TypeError, InvalidOperation, Item.DoesNotExist, User.DoesNotExist):
        return Response({"error": "Dữ liệu không hợp lệ hoặc đối tượng không tồn tại."}, status=status.HTTP_400_BAD_REQUEST)

    # --- 2. KIỂM TRA CÁC ĐIỀU KIỆN ĐẤU GIÁ CƠ BẢN ---
    if item.status != 'ongoing' or timezone.now() > item.end_time:
        return Response({"error": "Phiên đấu giá đã kết thúc."}, status=status.HTTP_400_BAD_REQUEST)

    # --- 3. LOGIC ĐẶT CỌC (Sử dụng đúng tên trường cho từng model) ---
    
    # Model Escrow dùng trường tên là 'item'
    has_paid_deposit = Escrow.objects.filter(item=item, user=user).exists()

    if not has_paid_deposit:
        deposit_amount = item.starting_price
        
        if bidder_db.balance < deposit_amount:
            return Response({"error_code": "INSUFFICIENT_FUNDS", "error": f"Số dư không đủ để đặt cọc. Cần thêm {deposit_amount - bidder_db.balance:,.0f} đ."}, status=status.HTTP_402_PAYMENT_REQUIRED)

        if not deposit_confirmed:
            return Response({
                "error_code": "DEPOSIT_REQUIRED",
                "message": f"Bạn phải cọc trước số tiền bằng giá khởi điểm là {deposit_amount:,.0f} VNĐ để tham gia.",
                "deposit_amount": deposit_amount
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        bidder_db.balance -= deposit_amount
        # Model Escrow dùng trường tên là 'item'
        Escrow.objects.create(item=item, user=user, amount=deposit_amount, status=Escrow.Status.HELD)
        
    # --- 4. XỬ LÝ ĐẶT GIÁ ---
    # Model Bid dùng trường tên là 'item_id'
    is_first_bid_ever = not Bid.objects.filter(item_id=item).exists()
    current_valid_price = item.starting_price if is_first_bid_ever else item.current_price
    
    if bid_amount < current_valid_price:
        return Response({"error": f"Giá của bạn phải lớn hơn hoặc bằng {current_valid_price:,.0f} đ."}, status=status.HTTP_400_BAD_REQUEST)
    if not is_first_bid_ever and bid_amount <= item.current_price:
        return Response({"error": f"Giá của bạn phải cao hơn giá hiện tại {item.current_price:,.0f} đ."}, status=status.HTTP_400_BAD_REQUEST)

    # Model Bid dùng trường tên là 'item_id' và 'user_id'
    bid_instance = Bid.objects.create(item_id=item, user_id=user, bid_amount=bid_amount)
    
    item.current_price = bid_amount
    item.current_highest_bid = bid_instance
    item.save()
    
    bidder_db.save()

    # --- 5. GỬI CẬP NHẬT REAL-TIME VÀ TRẢ VỀ KẾT QUẢ ---
    # (Phần này giữ nguyên)
    try:
        channel_layer = get_channel_layer()
        item_group_name = f'item_bid_{item.pk}'
        item_details_data = get_item_details_for_socket(item)
        bid_history_data = get_bid_history_for_socket(item)
        async_to_sync(channel_layer.group_send)(
            item_group_name, {
                'type': 'bid_update',
                'item_details': item_details_data,
                'bid_history': bid_history_data,
                'new_highest_bid': str(item.current_price),
                'bidder_info': {'user_id': user.pk, 'email': user.email}
            }
        )
    except Exception as e:
        print(f"Error sending WebSocket update: {e}")

    return Response({"success": True, "message": "Đặt giá thành công!"}, status=status.HTTP_201_CREATED)




# API 2: Lấy danh sách giá thầu của một sản phẩm
@api_view(['POST'])
@permission_classes([IsAuthenticated]) # Hoặc AllowAny nếu muốn ai cũng xem được
def get_bids_for_item(request):
    item_id_str = request.data.get('item_id')
    if not item_id_str:
        return Response({"error": "Thiếu item_id!"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        item_id = int(item_id_str)
    except ValueError:
        return Response({"error": "Item ID không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)

    item = get_object_or_404(Item, pk=item_id)
    # Sử dụng hàm helper để đảm bảo dữ liệu nhất quán với WebSocket nếu cần
    # Hoặc dùng serializer như cũ nếu JS gọi API này riêng và tự xử lý
    bids_data = get_bid_history_for_socket(item, limit=None) # Lấy toàn bộ nếu limit=None
    return Response(bids_data, status=status.HTTP_200_OK)
    # Hoặc giữ nguyên nếu serializer của bạn đã đủ tốt:
    # bids = Bid.objects.filter(item_id=item).order_by('-bid_time').select_related('user_id')
    # serializer = Bidserializers(bids, many=True)
    # return Response(serializer.data, status=status.HTTP_200_OK)


# API 3: Lấy giá thầu cao nhất của một sản phẩm (Ít dùng nếu đã có real-time)
@api_view(['POST'])
@permission_classes([IsAuthenticated]) # Hoặc AllowAny
def get_highest_bid(request):
    # API này có thể không cần thiết nếu client luôn có giá cao nhất qua WebSocket
    # hoặc qua get_item_details_for_socket
    item_id_str = request.data.get('item_id')
    if not item_id_str:
        return Response({"error": "Thiếu item_id!"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        item_id = int(item_id_str)
    except ValueError:
        return Response({"error": "Item ID không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)

    item = get_object_or_404(Item, pk=item_id)
    highest_bid = Bid.objects.filter(item_id=item).order_by('-bid_amount', '-bid_time').first()

    if highest_bid:
        serializer = Bidserializers(highest_bid) # Đảm bảo serializer này có user_detail
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response({"message": "Chưa có giá thầu nào cho sản phẩm này."}, status=status.HTTP_200_OK)

# View cho trang chi tiết đấu giá (HTML)
def bidding_detail_view(request, pk):
    item = get_object_or_404(Item, pk=pk)
    # Logic xử lý kết thúc phiên được loại bỏ, giả định tác vụ nền và WebSocket xử lý
    bids = Bid.objects.filter(item_id=item).order_by('-bid_time')[:10]
    context = {
        'item': item,
        'bids': bids,
    }
    return render(request, 'bidding/bidding_detail.html', context)

@login_required
@require_POST
def cancel_my_bid_view(request):
    try:
        data = json.loads(request.body)
        item_id_str = data.get('item_id')
        nguoi_dung_hien_tai = request.user

        if not item_id_str:
            return JsonResponse({'success': False, 'error': 'Thiếu item_id.'}, status=400)
        try:
            item_id = int(item_id_str)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Item ID không hợp lệ.'}, status=400)

        san_pham = get_object_or_404(Item, pk=item_id) # Nên là item, không phải san_pham
                                                       # để nhất quán, nhưng giữ theo code gốc của bạn
        thoi_gian_hien_tai_utc = timezone.now()

        if san_pham.status != 'ongoing' or not (san_pham.end_time and san_pham.end_time > thoi_gian_hien_tai_utc):
            return JsonResponse({'success': False, 'error': 'Không thể hủy bid cho phiên đấu giá đã kết thúc, bị hủy hoặc không hợp lệ.'}, status=400)

        bid_cao_nhat_cua_nguoi_dung = Bid.objects.filter(
            item_id=san_pham,
            user_id=nguoi_dung_hien_tai
        ).order_by('-bid_amount', '-bid_time').first()

        if not bid_cao_nhat_cua_nguoi_dung:
            return JsonResponse({'success': False, 'error': 'Bạn không có bid nào để hủy cho sản phẩm này.'}, status=400)

        gia_bid_can_xoa = bid_cao_nhat_cua_nguoi_dung.bid_amount
        
        with django_db_transaction.atomic():
            bid_cao_nhat_cua_nguoi_dung.delete()
            bid_cao_nhat_con_lai = Bid.objects.filter(item_id=san_pham).order_by('-bid_amount', '-bid_time').first()

            if bid_cao_nhat_con_lai:
                san_pham.current_price = bid_cao_nhat_con_lai.bid_amount
            else:
                san_pham.current_price = san_pham.starting_price if san_pham.starting_price > 0 else Decimal('0')
            san_pham.save(update_fields=['current_price'])

        # --- GỬI THÔNG BÁO REAL-TIME SAU KHI HỦY BID ---
        channel_layer = get_channel_layer()
        item_group_name = f'item_bid_{san_pham.pk}'

        item_details_data = get_item_details_for_socket(san_pham) # san_pham đã cập nhật current_price
        bid_history_data = get_bid_history_for_socket(san_pham)   # Lịch sử bid đã thay đổi

        async_to_sync(channel_layer.group_send)(
            item_group_name,
            {
                'type': 'bid_update', # Dùng lại type này, JS sẽ cập nhật UI
                'item_details': item_details_data,
                'bid_history': bid_history_data,
                'new_highest_bid': str(san_pham.current_price),
                'action_info': { # Thêm thông tin về hành động nếu JS cần
                    'action_type': 'bid_canceled',
                    'canceled_by_user_email': nguoi_dung_hien_tai.email,
                    'canceled_bid_amount': str(gia_bid_can_xoa)
                }
            }
        )

        async_to_sync(channel_layer.group_send)(
            'homepage_items',
            {
                'type': 'bid_update',
                'item_details': item_details_data
            }
        )
        # ----------------------------------

        return JsonResponse({
            'success': True,
            'message': f'Đã hủy lượt đặt giá {gia_bid_can_xoa:,.0f} VNĐ thành công.',
            'new_current_price_formatted': f"{san_pham.current_price:,.0f} VNĐ",
            'itemId': san_pham.pk
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Dữ liệu gửi lên không hợp lệ.'}, status=400)
    except Item.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Sản phẩm không tồn tại.'}, status=404)
    except Exception as e:
        print(f"Cancel bid API error: {e}")
        return JsonResponse({'success': False, 'error': 'Đã xảy ra lỗi không mong muốn khi hủy bid.'}, status=500)

@login_required
def my_active_bids_view(request):
    nguoi_dung_hien_tai = request.user
    thoi_gian_hien_tai_utc = timezone.now()

    # Lấy ID các sản phẩm mà người dùng này đã từng đặt giá
    id_cac_san_pham_da_dau_gia = Bid.objects.filter(user_id=nguoi_dung_hien_tai)\
                                        .values_list('item_id', flat=True).distinct()
    
    danh_sach_san_pham_da_dau_gia = Item.objects.filter(pk__in=id_cac_san_pham_da_dau_gia)\
                                            .select_related('seller')\
                                            .order_by(
                                                Case(
                                                    When(status='ongoing', end_time__gt=thoi_gian_hien_tai_utc, then=Value(0)), 
                                                    default=Value(1)
                                                ), 
                                                '-end_time'
                                            )

    thong_tin_san_pham_kem_trang_thai = []
    
    for san_pham_item in danh_sach_san_pham_da_dau_gia:
        # Xử lý các phiên đấu giá đã kết thúc (nếu chưa được xử lý bởi Celery)
        if san_pham_item.status == 'ongoing' and san_pham_item.end_time and san_pham_item.end_time <= thoi_gian_hien_tai_utc:
            print(f"Item {san_pham_item.pk} ({san_pham_item.name}) in my_active_bids_view needs end-of-auction processing.")
            if xu_ly_phien_dau_gia_ket_thuc(san_pham_item.pk):
                san_pham_item.refresh_from_db()
                print(f"Processed item {san_pham_item.pk}, new status: {san_pham_item.status}")
            else:
                print(f"Failed to process ended auction for item {san_pham_item.pk}.")

        bid_cao_nhat_hien_tai_cua_toi_obj = Bid.objects.filter(
            item_id=san_pham_item,
            user_id=nguoi_dung_hien_tai
        ).order_by('-bid_amount', '-bid_time').first()

        gia_thau_cao_nhat_cua_nguoi_dung = bid_cao_nhat_hien_tai_cua_toi_obj.bid_amount if bid_cao_nhat_hien_tai_cua_toi_obj else Decimal('0')
        bid_id_cao_nhat_cua_toi_cho_huy = bid_cao_nhat_hien_tai_cua_toi_obj.bid_id if bid_cao_nhat_hien_tai_cua_toi_obj else None
        
        trang_thai_san_pham_cho_nguoi_dung = "Không xác định"
        ten_nut_hanh_dong_chinh = ""
        url_nut_hanh_dong_chinh = "" # Sẽ không dùng cho nút "Thanh Toán" kiểu JS
        class_css_nut_hanh_dong_chinh = "btn-secondary" # Mặc định
        hien_thi_nut_huy = False
        # Các biến cho nút "Thanh Toán" kiểu JS
        is_payment_button = False 
        payment_item_id = None
        payment_buyer_id = None
        payment_seller_id = None
        payment_final_price = None

        if san_pham_item.status == 'ongoing':
            trang_thai_san_pham_cho_nguoi_dung = "Đang đấu giá"
            ten_nut_hanh_dong_chinh = "Đặt giá lại"
            if bid_cao_nhat_hien_tai_cua_toi_obj:
                hien_thi_nut_huy = True
            try:
                url_nut_hanh_dong_chinh = reverse('bidding-detail-page', kwargs={'pk': san_pham_item.pk})
            except Exception:
                url_nut_hanh_dong_chinh = "#"
            class_css_nut_hanh_dong_chinh = "btn-primary"

        elif san_pham_item.status == 'completed': # Đấu giá đã kết thúc
            # Kiểm tra xem người dùng này có thắng và đã có GiaoDichThanhToan chưa
            giao_dich_thang_cuoc_cua_toi = Transaction.objects.filter(
                item_id=san_pham_item, 
                buyer_id=nguoi_dung_hien_tai
            ).first()
            
            if giao_dich_thang_cuoc_cua_toi: # Người dùng này thắng và có giao dịch
                if giao_dich_thang_cuoc_cua_toi.status == 'completed':
                    trang_thai_san_pham_cho_nguoi_dung = "Đã thanh toán"
                    ten_nut_hanh_dong_chinh = "Xem chi tiết GD" # Hoặc "Xem sản phẩm"
                    # URL có thể là chi tiết giao dịch hoặc chi tiết sản phẩm
                    try: url_nut_hanh_dong_chinh = reverse('item-detail-template', kwargs={'pk': san_pham_item.pk})
                    except: url_nut_hanh_dong_chinh = "#"
                    class_css_nut_hanh_dong_chinh = "btn-info"
                elif giao_dich_thang_cuoc_cua_toi.status == 'pending':
                    trang_thai_san_pham_cho_nguoi_dung = "Đấu giá thành công" # Chờ thanh toán
                    # Thiết lập thông tin cho nút "Thanh Toán" kiểu JavaScript
                    is_payment_button = True
                    payment_item_id = san_pham_item.pk
                    payment_buyer_id = nguoi_dung_hien_tai.pk
                    payment_seller_id = san_pham_item.seller_id # Đảm bảo seller_id là ID, không phải object
                    payment_final_price = giao_dich_thang_cuoc_cua_toi.final_price
                    # ten_nut_hanh_dong_chinh và class_css_nut_hanh_dong_chinh sẽ được xử lý trong template dựa trên is_payment_button
                else: # Giao dịch thanh toán bị 'failed' hoặc trạng thái khác
                    trang_thai_san_pham_cho_nguoi_dung = f"GD thanh toán: {giao_dich_thang_cuoc_cua_toi.get_status_display()}"
                    ten_nut_hanh_dong_chinh = "Xem sản phẩm"
                    try: url_nut_hanh_dong_chinh = reverse('item-detail-template', kwargs={'pk': san_pham_item.pk})
                    except: url_nut_hanh_dong_chinh = "#"
                    class_css_nut_hanh_dong_chinh = "btn-warning"
            else: # Đấu giá kết thúc nhưng người này không thắng (hoặc chưa có GiaoDichThanhToan được tạo cho họ)
                # Kiểm tra xem có phải là người thắng không dựa trên Bid cao nhất
                bid_thang_cuoc_tong = Bid.objects.filter(item_id=san_pham_item).order_by('-bid_amount', '-bid_time').first()
                if bid_thang_cuoc_tong and bid_thang_cuoc_tong.user_id == nguoi_dung_hien_tai:
                    # Trường hợp này không nên xảy ra nếu logic tạo GiaoDichThanhToan khi kết thúc đấu giá là đúng
                    # Nhưng nếu xảy ra, nghĩa là họ thắng nhưng chưa có GiaoDichThanhToan
                    trang_thai_san_pham_cho_nguoi_dung = "Đấu giá thành công (Lỗi GD)" 
                    # Cần xem lại logic tạo GiaoDichThanhToan
                else:
                    trang_thai_san_pham_cho_nguoi_dung = "Đấu giá thất bại"
                ten_nut_hanh_dong_chinh = "Xem sản phẩm"
                try: url_nut_hanh_dong_chinh = reverse('item-detail-template', kwargs={'pk': san_pham_item.pk})
                except: url_nut_hanh_dong_chinh = "#"
        
        elif san_pham_item.status == 'canceled':
            trang_thai_san_pham_cho_nguoi_dung = "Phiên bị hủy"
            ten_nut_hanh_dong_chinh = "Xem sản phẩm"
            try: url_nut_hanh_dong_chinh = reverse('item-detail-template', kwargs={'pk': san_pham_item.pk})
            except: url_nut_hanh_dong_chinh = "#"
            class_css_nut_hanh_dong_chinh = "btn-secondary"
        
        # ... (các else if cho các trạng thái khác của item nếu có) ...

        thong_tin_san_pham_kem_trang_thai.append({
            'item': san_pham_item,
            'gia_cao_nhat_cua_toi': gia_thau_cao_nhat_cua_nguoi_dung,
            'bid_id_cao_nhat_cua_toi': bid_id_cao_nhat_cua_toi_cho_huy, # Đổi tên biến cho rõ ràng
            'trang_thai_cho_toi': trang_thai_san_pham_cho_nguoi_dung,
            
            # Cho các nút hành động chung (không phải nút payment JS)
            'chu_tren_nut_hanh_dong': ten_nut_hanh_dong_chinh if not is_payment_button else "", 
            'url_cho_nut_hanh_dong': url_nut_hanh_dong_chinh if not is_payment_button else "",
            'class_css_cho_nut_hanh_dong': class_css_nut_hanh_dong_chinh if not is_payment_button else "",
            
            'hien_thi_nut_huy_dau_gia': hien_thi_nut_huy,

            # Thông tin riêng cho nút "Thanh Toán" kiểu JavaScript
            'is_payment_button': is_payment_button,
            'payment_item_id': payment_item_id,
            'payment_buyer_id': payment_buyer_id,
            'payment_seller_id': payment_seller_id,
            'payment_final_price': payment_final_price,
        })

    context = {
        'page_title': 'Sản phẩm đang theo dõi & Kết quả',
        'active_bids_info': thong_tin_san_pham_kem_trang_thai,
        'now_utc': thoi_gian_hien_tai_utc, # Đổi tên cho nhất quán
        # 'csrf_token_value': request.COOKIES.get('csrftoken') # Không cần thiết, dùng thẻ {% csrf_token %} trong form nếu có, hoặc JS tự lấy cookie
    }
    return render(request, 'bidding/my_active_bids.html', context)

@api_view(['POST'])
@permission_classes([IsAuthenticated]) # Yêu cầu người dùng phải đăng nhập mới được kích hoạt
def process_single_ended_auction(request):
    """
    API này được gọi bởi Javascript phía client khi đồng hồ đếm ngược kết thúc.
    Nó chỉ xử lý cho một item cụ thể được gửi lên.
    """
    item_id = request.data.get('item_id')
    if not item_id:
        return Response({"error": "Item ID is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with django_db_transaction.atomic():
            # Khóa sản phẩm lại để tránh 2 người gọi API cùng lúc gây lỗi
            item = Item.objects.select_for_update().get(pk=item_id)

            # Chỉ xử lý nếu phiên đấu giá thực sự đã kết thúc và đang 'ongoing'
            if item.status == 'ongoing' and item.end_time and timezone.now() > item.end_time:
                
                # --- LOGIC HOÀN TIỀN CHO NGƯỜI THUA ---
                # Sửa lại .user thành .user_id cho đúng với model Bid của bạn
                winning_bid = item.current_highest_bid
                winner = winning_bid.user_id if winning_bid else None
                
                all_escrows = Escrow.objects.filter(item_id=item, status=Escrow.Status.HELD).select_related('user')

                for escrow in all_escrows:
                    if escrow.user != winner:
                        # HOÀN TIỀN CHO NGƯỜI THUA
                        loser = escrow.user
                        loser.balance += escrow.amount
                        loser.save(update_fields=['balance'])
                        
                        escrow.status = Escrow.Status.REFUNDED
                        escrow.save(update_fields=['status'])
                        print(f"Refunded {escrow.amount} to {loser.email} for item {item.name}")

                # =======================================================
                # BỔ SUNG LOGIC CÒN THIẾU: TẠO GIAO DỊCH CHO NGƯỜI THẮNG
                # =======================================================
                if winner:
                    # Kiểm tra để chắc chắn chưa có giao dịch nào được tạo
                    transaction_exists = Transaction.objects.filter(item_id=item, buyer_id=winner).exists()
                    if not transaction_exists:
                        Transaction.objects.create(
                            item_id=item,
                            buyer_id=winner,
                            seller_id=item.seller,
                            final_price=winning_bid.bid_amount,
                            status='pending'  # Hoặc 'PENDING_PAYMENT' tùy theo model Transaction của bạn
                        )
                        print(f"Created pending transaction for winner {winner.email} for item {item.name}")
                # =======================================================

                # Đóng phiên đấu giá
                item.status = 'completed'
                item.save(update_fields=['status'])

                # Gửi thông báo real-time đến tất cả mọi người
                channel_layer = get_channel_layer()
                item_group_name = f'item_bid_{item.pk}'
                winner_info = {'email': winner.email, 'bid_amount': str(item.current_price)} if winner else None
                
                async_to_sync(channel_layer.group_send)(
                    item_group_name,
                    {
                        'type': 'auction_ended_update',
                        'item_details': get_item_details_for_socket(item),
                        'winner_info': winner_info,
                        'message': f"Phiên đấu giá cho '{item.name}' đã kết thúc."
                    }
                )
                
                return Response({"status": "success", "message": "Auction processed successfully."}, status=status.HTTP_200_OK)
            
            else:
                # Phiên đấu giá chưa sẵn sàng để đóng hoặc đã được xử lý rồi
                return Response({"status": "noop", "message": "Auction not ready or already processed."}, status=status.HTTP_200_OK)

    except Item.DoesNotExist:
        return Response({"error": "Item not found."}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Error processing single ended auction: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@login_required
def my_created_items_view(request):
    user = request.user
    items = Item.objects.filter(seller=user).order_by('-item_id')  # hoặc .order_by('-end_time')
    
    active_bids_info = []
    for item in items:
        thong_tin = {
            'item': item,
            'trang_thai_cho_toi': item.get_status_display(),  # hoặc định nghĩa logic riêng
        }
        active_bids_info.append(thong_tin)

    context = {
        'active_bids_info': active_bids_info,
        'page_title': "Sản phẩm bạn đã tạo",
        'now': now(),
    }
    return render(request, 'bidding/my_created_bids.html', context)