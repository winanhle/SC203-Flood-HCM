# Báo cáo bổ sung và kiểm định dữ liệu ngập TP.HCM

**Nhánh làm việc:** `codex/verified-spatial-imerg-enrichment`

**Ngày báo cáo:** 07/11/2026
**Phạm vi:** Bổ sung biến vật lý phục vụ kiểm định H1; không thay đổi dữ liệu gốc và chưa diễn giải đây là kết quả kiểm định H1.

## 1. Mục tiêu

Nhóm thực hiện ba việc:

1. Giữ nguyên protocol chia fold chống rò rỉ dữ liệu: các dòng có liên hệ qua địa điểm, nguồn hoặc ngày được đặt trong cùng connected component.
2. Thay biến không gian dạng tên quận/huyện bằng tọa độ, cao độ và khoảng cách tới sông/kênh.
3. Thay lượng mưa tại một điểm tham chiếu chung bằng lượng mưa tại ô lưới chứa từng quan sát ngập.

## 2. Nguồn dữ liệu và lý do lựa chọn

### 2.1. Tọa độ quan sát và thủy hệ

Nguồn chính là bộ dữ liệu của Hardy và Radziute (2026), *Historical database of urban flooding in Ho Chi Minh City, Vietnam (2002-2026)*, DataSuds, DOI: https://doi.org/10.23708/8Y16HU.

- `HCMC_Floods_BDD.gpkg`: 425 điểm ngập, CRS VN-2000 TM-3 105-45 (EPSG:9210).
- `HCMC_water.gpkg`: 2.430 polygon sông, kênh và mặt nước.
- MD5 của hai file khớp metadata trên DataSuds.
- SHA-256 được ghi trong `data/enrichment_audit.json` để kiểm tra file sử dụng trong phân tích.

Không geocode lại tên đường bằng Nominatim hoặc Google Maps. Tọa độ được lấy trực tiếp từ layer điểm do tác giả dữ liệu công bố, vì layer này bảo toàn phương pháp geocoding và trường `Spatial_precision` của nghiên cứu gốc.

Khoảng cách tới thủy hệ được tính trong EPSG:9210, đơn vị mét, từ điểm quan sát tới polygon nước gần nhất.

### 2.2. Lượng mưa

Nguồn mưa là NASA GPM IMERG V07, biến `IMERG_PRECTOT`, truy cập qua NASA POWER Daily API:

- Tài liệu nguồn: https://power.larc.nasa.gov/docs/methodology/data/sources_meteorology/
- Tài liệu API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- Độ phân giải không gian: 0,1 độ, xấp xỉ 10 km.
- Độ phân giải thời gian: ngày, tổng lượng mưa mm/ngày.
- Chuẩn thời gian: UTC.
- Phạm vi IMERG theo tài liệu NASA bao phủ toàn bộ giai đoạn quan sát 2002-2026.

Mỗi quan sát được gán vào ô IMERG 0,1 độ chứa tọa độ của nó. Pipeline chỉ truy vấn một lần cho mỗi ô lưới; 362 quan sát có ngày nằm trong 13 ô IMERG khác nhau. Các biến được tạo gồm:

- `rain_imerg_site_day_mm`: mưa trong ngày mang nhãn ngày sự kiện;
- `rain_imerg_site_prev1d_mm`: mưa ngày liền trước;
- `rain_imerg_site_prev3d_mm`: tổng ba ngày trước sự kiện;
- `rain_imerg_site_prev7d_mm`: tổng bảy ngày trước sự kiện.

Các tổng antecedent không bao gồm ngày sự kiện.

### 2.3. Cao độ

Cao độ lấy từ Copernicus DEM GLO-90 2021, độ phân giải 90 m, thông qua Open-Meteo Elevation API:

- Tài liệu API và nguồn DEM: https://open-meteo.com/en/docs/elevation-api
- DOI Copernicus DEM: https://doi.org/10.5270/ESA-c5d3d65

## 3. Kiểm định việc nối dữ liệu

`Obs_id` của dữ liệu công bố có một giá trị trùng, nên không được dùng làm khóa duy nhất. Pipeline dùng `OBJECTID` của bảng gốc làm khóa nối ổn định.

Trước khi nối geometry, chương trình kiểm tra thứ tự và sự trùng khớp của cả 425 dòng trên ngày cùng toàn bộ 21 thuộc tính phi hình học dùng chung giữa file TAB và GeoPackage. Kết quả không có dòng lệch. Hai giá trị literal `<Nul>` trong GeoPackage được chuẩn hóa tương đương ô trống; 13 giá trị duration dùng dấu phẩy thập phân trong TAB được chuẩn hóa trước khi đối chiếu.

Sau khi nối, chương trình kiểm tra:

- 425 `OBJECTID` duy nhất;
- không thay đổi số dòng hoặc thứ tự dòng gốc;
- 425/425 dòng có tọa độ và cao độ; 423/425 dòng có khoảng cách thủy hệ hợp lệ trong phạm vi layer nước;
- mưa chỉ xuất hiện ở đúng 362 dòng có ngày; 63 dòng thiếu ngày vẫn để trống;
- không thay giá trị thiếu bằng 0;
- các biến khoảng cách, cao độ và lượng mưa không âm.

Năm mẫu thuộc năm ô IMERG khác nhau được truy vấn lại trực tiếp tại tọa độ quan sát. Giá trị mưa ngày và tổng 1/3/7 ngày đều khớp với bảng đã tạo. NASA POWER trả về nguồn `IMERG`, API version `v2.10.3`, time standard `UTC`. Báo cáo máy đọc nằm tại `results/enrichment_validation.json` và có trạng thái `PASS`.

## 4. Coverage sau enrichment

| Tập dữ liệu | Số dòng |
|---|---:|
| Tổng quan sát gốc | 425 |
| Có tọa độ + cao độ | 425 |
| Có khoảng cách thủy hệ trong phạm vi layer | 423 |
| Có ngày chính xác + mưa IMERG | 362 |
| Có `Water height max` dạng số | 147 |
| Có nhãn `Depth class` | 168 |
| Có depth số + ngày + mưa | 123 |
| Có depth class + ngày + mưa | 139 |
| Có depth class + spatial, không bắt buộc mưa | 168 |

Enrichment không làm tăng số nhãn regression: target số vẫn là 147 dòng. Giá trị của bước này là cung cấp biến mưa và spatial đúng nghĩa. Việc chuyển sang classification tận dụng thêm 21 dòng có `Depth class` nhưng không có độ sâu số, tăng từ 147 lên 168 dòng có nhãn.

## 5. Hạn chế cần ghi trong báo cáo nghiên cứu

1. IMERG là dữ liệu lưới khoảng 10 km, không phải trạm mưa tại mặt đường; không thể mô tả mưa đối lưu ở quy mô đường phố.
2. IMERG Daily dùng UTC, trong khi sự kiện được ghi theo ngày địa phương và không có giờ xảy ra. Một ngày UTC chạy từ 07:00 ICT đến 07:00 ICT hôm sau. Vì vậy cần chạy sensitivity analysis với mưa ngày sự kiện, ngày trước đó và tích lũy 3/7 ngày.
3. 63 quan sát không có ngày chính xác. Nhóm không suy diễn ngày từ cột `Year`, vì làm vậy sẽ tạo dữ liệu giả.
4. DEM GLO-90 có độ phân giải 90 m; chênh lệch cao độ nhỏ trong địa hình bằng phẳng của TP.HCM phải được diễn giải thận trọng.
5. Khoảng cách tới nước phụ thuộc độ đầy đủ của layer thủy hệ công bố.
   Hai điểm tại Bà Rịa-Vũng Tàu nằm ngoài bounding box của layer nước nên được để missing và gắn cờ, thay vì dùng khoảng cách sai tới mép dữ liệu. Một khoảng cách trong phạm vi layer lớn hơn 5 km được gắn cờ để sensitivity analysis.
6. Dữ liệu ngập là dữ liệu sự kiện được báo chí/nguồn kỹ thuật ghi nhận, nên vẫn có selection bias.
7. Trang DataSuds hiện ghi CC BY-NC 4.0, trong khi README đi kèm ghi CC BY 4.0. Nhóm áp dụng điều kiện bảo thủ hơn là CC BY-NC 4.0 cho đến khi có xác nhận từ chủ dữ liệu.

## 6. Bước mô hình hóa đề xuất

Trên cùng các fold connected-component chống leakage, chạy và báo cáo riêng:

1. rainfall-only;
2. rainfall + historical context;
3. rainfall + historical context + elevation + distance to water.

Thực hiện cả regression trên tập complete-case 123 dòng và classification trên tập 139 dòng có mưa. Có thể bổ sung classification spatial-only trên 168 dòng như một sensitivity analysis, nhưng không được so trực tiếp metric của tập 168 dòng với metric của tập 139 dòng nếu không ghi rõ khác sample.

## 7. Nội dung ngắn có thể gửi thầy

> Dạ nhóm em đã kiểm tra lại phần dữ liệu bổ sung theo hướng có thể tái lập. Tọa độ của 425 quan sát không được geocode lại mà lấy trực tiếp từ GeoPackage chính thức của bộ DataSuds; nhóm đã đối chiếu cả 425 dòng trên ngày và 21 thuộc tính với bảng TAB trước khi nối. Từ tọa độ này, nhóm tính cao độ Copernicus GLO-90 và khoảng cách tới layer sông/kênh trong cùng bộ dữ liệu. Hai điểm ngoài bounding box của layer nước được để missing thay vì dùng khoảng cách sai tới mép dữ liệu, nên coverage khoảng cách hợp lệ là 423/425. Lượng mưa được thay bằng NASA GPM IMERG V07 tại ô lưới 0,1 độ chứa từng quan sát, gồm mưa ngày sự kiện và tích lũy 1/3/7 ngày trước đó. Hiện 362 dòng có ngày và mưa; tập regression đầy đủ depth+rain còn 123 dòng, còn classification đầy đủ class+rain có 139 dòng (168 dòng nếu chạy spatial-only). Nhóm không điền mưa cho 63 dòng thiếu ngày và không coi missing là 0. Pipeline validation đã PASS, gồm truy vấn lại độc lập 5 vị trí từ NASA POWER. Bước tiếp theo nhóm sẽ chạy ba cấu hình rainfall-only, rainfall+historical và rainfall+historical+spatial trên cùng fold chống leakage, đồng thời ghi rõ giới hạn IMERG daily UTC và độ phân giải khoảng 10 km.
