# views.py
from django.shortcuts import get_object_or_404 # Dùng cái này tiện hơn try-except
from rest_framework import status, permissions # Thêm permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User
from .serializers import UserSerializer # Đổi tên serializer cho đúng chuẩn Python (viết hoa)
from rest_framework.parsers import MultiPartParser, FormParser # Thêm parser cho file upload

# View để lấy danh sách User (Thường chỉ dành cho Admin)
class UserList(APIView):
    permission_classes = [permissions.IsAdminUser] # Chỉ Admin mới được xem list users

    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    # POST để tạo user mới thường không nằm ở đây, mà ở view đăng ký riêng
    # def post(self, request):
    #     ... (nên bỏ hoặc chuyển qua view register)

# View để xem/sửa/xóa một User cụ thể bằng ID (Thường chỉ dành cho Admin)
class UserDetail(APIView):
    permission_classes = [permissions.IsAdminUser] # Chỉ Admin mới được thao tác trên user khác

    def get_object(self, pk):
        # Sửa lại: Tìm user bằng primary key (id)
        return get_object_or_404(User, pk=pk) 
    
    def get(self, request, pk):
        user = self.get_object(pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    def put(self, request, pk):
        user = self.get_object(pk)
        # Lưu ý: PUT thường yêu cầu đủ các trường, PATCH thì chỉ cần trường cần update
        # Cân nhắc dùng PATCH nếu chỉ muốn update một phần
        serializer = UserSerializer(user, data=request.data) 
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        user = self.get_object(pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# ----- CÁC VIEW MỚI CHO PROFILE -----

class UserProfileView(APIView):
    """
    View để user đang đăng nhập xem thông tin profile của chính mình.
    Endpoint: /api/profile/me/ (Ví dụ)
    """
    permission_classes = [permissions.IsAuthenticated] # Yêu cầu user phải đăng nhập

    def get(self, request):
        """Trả về thông tin của user đang đăng nhập."""
        user = request.user # Lấy thẳng user từ request
        serializer = UserSerializer(user)
        return Response(serializer.data)

    # Có thể thêm method PATCH ở đây để cho phép user cập nhật một số trường 
    # (ví dụ: first_name, last_name nếu có trong model và serializer)
    # def patch(self, request):
    #     user = request.user
    #     serializer = UserSerializer(user, data=request.data, partial=True) # partial=True cho phép update từng phần
    #     if serializer.is_valid():
    #          # Chỉ cho phép update các trường cụ thể, không cho update email, balance ở đây
    #          allowed_updates = {'profile_picture'} # Chỉ ví dụ, ảnh nên có view riêng
    #          update_data = {k: v for k, v in serializer.validated_data.items() if k in allowed_updates}
             
    #          # Nên kiểm tra xem có dữ liệu update không trước khi save
    #          if update_data:
    #               serializer.save(**update_data) # Chỉ save các trường được phép

    #          # Trả về dữ liệu đã cập nhật (hoặc dữ liệu gốc nếu không có gì thay đổi)
    #          updated_serializer = UserSerializer(user) # Lấy lại dữ liệu mới nhất
    #          return Response(updated_serializer.data)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class ProfilePictureUploadView(APIView):
    """
    View để user upload ảnh đại diện mới.
    Endpoint: /api/profile/avatar/ (Ví dụ)
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser] # Cần parser này để xử lý file upload

    def post(self, request, format=None):
        """Nhận file ảnh và cập nhật profile_picture."""
        user = request.user
        # 'profile_picture' là tên key trong FormData gửi từ frontend
        if 'profile_picture' not in request.FILES:
            return Response({'detail': 'Không tìm thấy file ảnh nào.'}, status=status.HTTP_400_BAD_REQUEST)
            
        file_obj = request.FILES['profile_picture']
        
        # Kiểm tra kích thước file (ví dụ giới hạn 5MB) - Nên làm ở cả frontend và backend
        if file_obj.size > 5 * 1024 * 1024: 
             return Response({'detail': 'Kích thước file quá lớn (tối đa 5MB).'}, status=status.HTTP_400_BAD_REQUEST)

        # Kiểm tra loại file (ví dụ chỉ cho phép ảnh)
        if not file_obj.content_type.startswith('image'):
             return Response({'detail': 'Định dạng file không hợp lệ. Chỉ chấp nhận file ảnh.'}, status=status.HTTP_400_BAD_REQUEST)

        # Lưu ảnh mới vào trường profile_picture của user
        user.profile_picture = file_obj
        user.save()
        
        # Trả về URL của ảnh mới (nếu có) hoặc thông báo thành công
        serializer = UserSerializer(user, context={'request': request}) # Thêm context để serializer tạo URL đầy đủ nếu cần
        return Response({'detail': 'Upload ảnh đại diện thành công!', 'profile_picture_url': serializer.data.get('profile_picture')}, status=status.HTTP_200_OK)

# View để user tự xóa tài khoản của mình
class DeleteCurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        # Có thể thêm bước xác nhận mật khẩu ở đây nếu muốn an toàn hơn
        user.delete()
        return Response({'detail': 'Tài khoản đã được xóa thành công.'}, status=status.HTTP_204_NO_CONTENT) # Hoặc 200 OK nếu muốn trả về message
    