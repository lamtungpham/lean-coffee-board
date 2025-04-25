# Lean Coffee Board

Một công cụ Lean Coffee trực tuyến, phối hợp Streamlit và Google Firestore để họp ý tưởng theo phong cách thực thời gian thực (multi-user).

## Tính năng

- **Tạo bảng họp** với chủ đề tuỳ chọn  
- **Thêm, chỉnh sửa, gộp, xóa** các thẻ (cards)  
- **Vote / Unvote** thẻ với giới hạn phiếu theo thành viên  
- **Kéo-thả (drag & drop)** để sắp xếp lại (tùy chọn qua `streamlit-sortables`)  
- **Đồng bộ nhiều người** qua Firestore, tự động làm mới mỗi 5s  
- **Tuỳ chỉnh** số phiếu tối đa, bật/tắt sắp xếp theo phiếu  

## Demo

Live demo: _(chèn URL Streamlit Cloud của bạn tại đây)_

## Bắt đầu

### Yêu cầu

- Python 3.7+  
- Tài khoản Firebase với Firestore đã bật  
- File Service Account JSON (tải về từ Firebase Console)  

### Cài đặt

1. **Clone repo**  
   ```bash
   git clone https://github.com/your-username/lean-coffee-board.git
   cd lean-coffee-board
