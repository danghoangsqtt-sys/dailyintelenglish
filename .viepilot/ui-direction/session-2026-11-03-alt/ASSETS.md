# Mascot VTuber — tạo ảnh bằng trang Nhân vật của ứng dụng

Mục tiêu: một mascot nửa người kiểu VTuber ở góc màn hình. Cô ấy thở, nghiêng đầu nhẹ, chớp mắt, mấp máy môi theo
giọng, đổi dáng tay và biểu cảm. Mình (Claude) ghép các ảnh thành một "con rối" chạy trong trình duyệt.

## Cách làm: dùng trang Nhân vật (không cần tự viết prompt)

Ứng dụng đã có quy trình này cho các nhân vật biết nói (Phase 32–33): mỗi hồ sơ nhân vật có **29 ô ảnh**, mỗi ô ghi sẵn
**ảnh cần đính kèm, vùng cần chọn để sửa và prompt**. Ảnh thả vào ô được tách nền xanh, căn theo ảnh gốc và kiểm tra
lệch tự động. Làm mascot là một hồ sơ nhân vật như mọi nhân vật khác, nên sau này cô ấy dùng được cả trong video.

1. Trang **Nhân vật** → tạo nhân vật mới: tên mascot, nữ, mô tả ngoại hình (tóc nâu đỏ dài gợn sóng rẽ ngôi giữa,
   kính tròn gọng đen, mắt nâu, hình trái tim đỏ nhỏ trên má trái), trang phục (áo sơ mi màu be cổ bẻ xắn tay, quần
   jean xanh). **Hướng nhìn: sang trái** (cô ấy đứng góc phải, nhìn về phía nội dung và bong bóng chat).
2. Ô ảnh gốc `calm__closed`: chép prompt của ô, **đổi chữ "Photorealistic." thành
   "Soft 3D cartoon style, exactly like the attached character pictures."**, đính kèm ảnh toàn thân và tờ khuôn mặt
   của mascot. Làm ảnh này thật đẹp vì mọi ảnh sau sửa từ nó.
3. Các ô còn lại: làm theo đúng ô (đính kèm ảnh ô chỉ định, chọn vùng mặt / mắt / miệng / tay rồi dán prompt). Ảnh nào
   bị báo lệch thì sửa lại từ ảnh gốc, không sửa tiếp từ ảnh lỗi.

Thứ tự nên làm: `calm__closed`, `calm__open`, `blink` (3 ảnh này đủ để mình dựng bản chạy đầu tiên: thở, chớp mắt,
mấp máy môi), rồi `smile`, `surprised`, `worried`, `thinking`, sau đó 7 dáng tay.

## 29 ô dùng vào việc gì ở góc màn hình

| Ô | Dùng khi |
|---|---|
| `calm` đóng / mở miệng, `blink` | đứng chờ, nói bình thường, chớp mắt |
| `smile`, `laugh` | chào, báo video đã xong |
| `surprised` | có việc mới cần bạn |
| `thinking` | AI đang chạy (viết kịch bản, tạo giọng, dựng video) |
| `worried` | có lỗi, thiếu hình |
| `serious` | nhắc việc quan trọng (sắp tới giờ đăng mà chưa duyệt) |
| `gesture-wave` | chào khi mở ứng dụng |
| `gesture-point` | chỉ về nút hoặc ô cần bấm |
| `gesture-talk`, `gesture-open` | giải thích, gợi ý |
| `gesture-think` | đang chờ AI |
| `gesture-heart` | cảm ơn, khi bạn duyệt xong |
| `gesture-listen` | đang nghe bạn nói |

Ảnh của trang Nhân vật là khung 1280×1536 từ đầu đến giữa đùi; mình cắt lấy nửa người cho góc màn hình.

## Thêm sau (không bắt buộc): nếu muốn mượt hơn nữa

Trang Nhân vật cho miệng hai trạng thái (đóng, mở). Muốn miệng mềm như VTuber hơn, có thể làm thêm vài ảnh bằng cùng
cách (đính kèm `calm__closed`, chọn vùng miệng hoặc mắt). Các quy tắc và danh sách dưới đây áp dụng cho các ảnh thêm này.

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

Ảnh thêm đặt vào thư mục `mascot/src/`, đúng tên file bên dưới. Nhóm 1, 4, 5 đã có trong 29 ô của trang Nhân vật,
chỉ cần làm khi không dùng trang đó.

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
