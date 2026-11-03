# Mascot VTuber — danh sách ảnh cần tạo (cho Codex)

Mục tiêu: một mascot nửa người kiểu VTuber ở góc màn hình. Cô ấy thở, nghiêng đầu nhẹ, chớp mắt, đảo mắt,
mấp máy môi theo giọng, đổi dáng tay và biểu cảm. Mình (Claude) ghép các ảnh dưới đây thành một "con rối" chạy trong
trình duyệt: tách nền, căn thẳng hàng, cắt riêng vùng mắt và miệng, rồi trộn mượt.

## Quy tắc chung (quan trọng nhất)

Mọi ảnh phải **khớp nhau như các khung hình của cùng một máy quay**, vì mắt và miệng sẽ được cắt từ ảnh này dán sang
ảnh khác:

1. **Khổ 1024 × 1024**, PNG. Nền **trong suốt**; nếu không được thì nền **xám phẳng #E6E3E8**, không bóng đổ, không
   chuyển màu.
2. **Nửa người**: từ đỉnh đầu đến ngang eo. Đỉnh tóc cách mép trên khoảng 60 px, eo chạm mép dưới. Nhân vật ở chính
   giữa, nhìn thẳng vào máy quay.
3. **Đầu giữ nguyên vị trí, cỡ và góc trong mọi ảnh** (trừ nhóm 6). Chỉ phần được nêu mới thay đổi.
4. Giữ đúng nhân vật: tóc nâu đỏ dài gợn sóng rẽ ngôi giữa, kính tròn gọng đen, mắt nâu, **hình trái tim đỏ nhỏ trên
   má trái của cô ấy** (bên phải người xem), áo sơ mi màu be cổ bẻ, xắn tay áo. Phong cách hoạt hình 3D mềm như ảnh
   gốc, cùng ánh sáng dịu từ phía trước.
5. Luôn **đính kèm ảnh `base.png`** khi tạo các ảnh sau, và yêu cầu "chỉ sửa phần X, giữ mọi thứ khác y hệt".
   Ảnh nào tóc, kính, áo hay vị trí đầu bị lệch thì làm lại.

Đặt tất cả ảnh vào thư mục `mascot/src/`, **đúng tên file** bên dưới.

## Nhóm 1 · Ảnh gốc (1 ảnh)

| File | Mô tả |
|---|---|
| `base.png` | Đứng thẳng, nhìn thẳng, mắt mở, miệng khép mỉm cười nhẹ, hai tay buông tự nhiên (bàn tay có thể khuất dưới mép ảnh). |

Prompt mẫu (đính kèm ảnh toàn thân và tờ khuôn mặt hiện có):
> Waist-up portrait of this exact character, 1024x1024, transparent background, centered, facing the camera,
> top of hair about 60 px from the top edge, waist touching the bottom edge. Neutral relaxed pose, arms down,
> mouth closed with a soft smile, eyes open. Same 3D cartoon style, outfit, glasses and the small red heart sticker
> on her left cheek. Soft front lighting, no shadow on the background.

## Nhóm 2 · Miệng (8 ảnh): chỉ đổi miệng

Prompt mẫu: *"Edit this image: change ONLY the mouth to {shape}. Keep everything else pixel-identical: same framing,
head position, hair, glasses, eyes, outfit, lighting."*

| File | Hình miệng |
|---|---|
| `mouth-closed.png` | khép, không cười |
| `mouth-slight.png` | hé nhẹ, thấy chút răng trên |
| `mouth-a.png` | mở to như nói "a" |
| `mouth-i.png` | kéo ngang, thấy răng, như nói "i" |
| `mouth-u.png` | chu tròn nhỏ, như nói "u" |
| `mouth-e.png` | mở vừa, kéo ngang nhẹ, như nói "e" |
| `mouth-o.png` | tròn vừa, như nói "o" |
| `mouth-laugh.png` | cười tươi mở miệng |

## Nhóm 3 · Mắt và lông mày (6 ảnh): chỉ đổi mắt, mày

| File | Mô tả |
|---|---|
| `eyes-half.png` | mắt khép một nửa (giữa lúc chớp) |
| `eyes-closed.png` | mắt nhắm (chớp) |
| `eyes-smile.png` | mắt cười cong hình ^ ^ |
| `eyes-left.png` | con ngươi nhìn sang trái của người xem |
| `eyes-right.png` | con ngươi nhìn sang phải của người xem |
| `brows-up.png` | lông mày nhướn lên, mắt mở to (ngạc nhiên) |

## Nhóm 4 · Dáng tay (7 ảnh): đầu và mặt giữ y hệt `base.png`, chỉ đổi tay và vai

| File | Dáng |
|---|---|
| `pose-wave.png` | giơ tay phải vẫy chào, lòng bàn tay hướng ra |
| `pose-point.png` | tay phải chỉ sang trái người xem, ngang ngực (chỉ về phía bong bóng chat) |
| `pose-explain.png` | hai bàn tay mở ngửa trước ngực, như đang giải thích |
| `pose-think.png` | ngón trỏ chạm cằm, đang suy nghĩ |
| `pose-thumbsup.png` | giơ ngón cái tay phải trước ngực |
| `pose-cheer.png` | hai tay nắm giơ lên ngang vai, vui mừng |
| `pose-sorry.png` | hai tay chắp trước ngực, như xin lỗi |

## Nhóm 5 · Biểu cảm cả khuôn mặt (3 ảnh): chỉ đổi mắt, mày, miệng

| File | Biểu cảm |
|---|---|
| `face-happy.png` | rất vui: mắt cười ^ ^, miệng cười mở |
| `face-worried.png` | lo lắng, áy náy: mày chau nhẹ, miệng mím (dùng khi có lỗi) |
| `face-focus.png` | tập trung: mắt hơi nheo, miệng khép (khi đang làm việc) |

## Nhóm 6 · Quay đầu (2 ảnh, không bắt buộc)

| File | Mô tả |
|---|---|
| `head-left.png` | quay đầu khoảng 15° sang trái người xem (nhìn về phía bong bóng chat), thân giữ nguyên |
| `head-right.png` | quay đầu khoảng 15° sang phải người xem, thân giữ nguyên |

## Mình sẽ làm gì với các ảnh

- Tách nền, căn thẳng hàng theo vị trí khuôn mặt, kiểm tra ảnh nào bị lệch.
- Cắt vùng mắt và vùng miệng thành các lớp nhỏ có viền mờ, để dán lên bất kỳ dáng tay nào.
- Chuyển động liên tục bằng mã: thở, đung đưa, nghiêng đầu nhẹ quanh cổ, chớp mắt ngẫu nhiên 3–6 giây, đảo mắt.
- Mấp máy môi: đo độ to của giọng VieNeu từng khung hình và chọn hình miệng, có làm mượt.
- Đổi dáng tay và biểu cảm bằng cách trộn mờ khoảng 0,2 giây, kèm một nhịp nhún nhẹ.
- Gắn với giao diện: vẫy khi chào, chỉ tay khi nói về một nút, ngón cái khi video làm xong, xin lỗi khi có lỗi, suy
  nghĩ khi AI đang chạy.
