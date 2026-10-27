# Hệ thống quản lý hội viên Cựu chiến binh — bản triển khai nền tảng

Đây là **bộ mã nguồn nền tảng để triển khai và kiểm thử**, không phải hệ thống đã được cơ quan có thẩm quyền phê duyệt hoặc đã được đưa lên Internet.

## Công nghệ
- Python / Flask
- PostgreSQL
- Hash mật khẩu bằng Werkzeug
- Flask-Login, CSRF protection, cookie HttpOnly/SameSite
- Phân quyền phía máy chủ theo đơn vị
- Nhật ký đăng nhập, thêm/sửa/xóa và xuất dữ liệu
- Xuất CSV có thể mở bằng Excel

## Sáu tài khoản dự kiến
- `tinh1`, `tinh2`, `tinh3`: quyền Tỉnh hội, phạm vi toàn tỉnh
- `myyen`: Hội CCB xã Mỹ Yên
- `benluc`: Hội CCB xã Bến Lức
- `tanninh`: Hội CCB phường Tân Ninh

**Không có mật khẩu mặc định trong mã nguồn.** Quản trị viên phải tự tạo sáu mật khẩu mạnh (tối thiểu 14 ký tự) trong môi trường triển khai, sau đó chạy `python seed_accounts.py` một lần. Không gửi mật khẩu qua nhóm chat hoặc đặt cùng một mật khẩu cho các tài khoản.

## Triển khai thử nghiệm có kiểm soát
1. Tạo repository riêng trong GitHub của đơn vị (không đưa dữ liệu hội viên thật vào Git).
2. Tạo PostgreSQL và web service ở nhà cung cấp được đơn vị phê duyệt.
3. Cấu hình `DATABASE_URL`, `SECRET_KEY`, `COOKIE_SECURE=true` và các biến `INITIAL_*_PASSWORD` trong mục Environment/Secrets của dịch vụ.
4. Chạy lệnh khởi tạo tài khoản `python seed_accounts.py` một lần trong môi trường đã cấu hình. Không để bước seed chạy tự động mỗi lần khởi động.
5. Xóa các biến `INITIAL_*_PASSWORD` sau khi tạo tài khoản, rồi kiểm tra đăng nhập và quyền truy cập.
6. Gắn tên miền do đơn vị quản lý, bắt buộc HTTPS, cấu hình cảnh báo, sao lưu PostgreSQL và kiểm thử phục hồi.
7. Kiểm thử với dữ liệu giả trước khi nghiệm thu.

## Các bước phải hoàn thiện trước khi dùng dữ liệu thật
- Xác nhận tên gọi đơn vị hành chính, cơ cấu tổ chức và phạm vi dữ liệu hiện hành.
- Thẩm định pháp lý, bảo vệ dữ liệu cá nhân, quy chế lưu trữ, quyền truy cập và thời hạn lưu.
- Bổ sung quy trình đổi/đặt lại mật khẩu, khóa tài khoản, MFA nếu phù hợp, giới hạn thử đăng nhập, cảnh báo và quản lý phiên.
- Đánh giá bảo mật độc lập; kiểm thử phân quyền bằng tài khoản của từng đơn vị.
- Thiết lập sao lưu mã hóa, bản sao ngoài hệ thống và diễn tập khôi phục.
- Xác định trường dữ liệu thực tế và quy trình nghiệp vụ (chuyển sinh hoạt, biến động, báo cáo chính thức) với Tỉnh hội.
- Cấu hình thời gian địa phương và hiển thị múi giờ phù hợp. Nhật ký hiện lưu UTC.
- Rà soát việc ghi nhật ký và tránh lưu dữ liệu cá nhân quá mức.

## Cảnh báo triển khai
Không sử dụng gói miễn phí hoặc dịch vụ ngủ/đóng băng theo thời gian nếu cần hệ thống nghiệp vụ liên tục. Cấu hình `render.yaml` chỉ là gợi ý khởi tạo; kiểm tra gói, vùng dữ liệu, chi phí, chính sách bảo mật, sao lưu và khả năng phục hồi trước khi triển khai. Không nhập dữ liệu hội viên thật cho đến khi được phê duyệt và nghiệm thu.

## Chạy local để lập trình (không dùng cho production)
Tạo môi trường ảo, cài `requirements.txt`, đặt `ALLOW_LOCAL_DEV=true`, `SECRET_KEY` ngẫu nhiên và `DATABASE_URL` tới PostgreSQL thử nghiệm. Không dùng dữ liệu thật trong môi trường phát triển.
