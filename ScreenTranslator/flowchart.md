# Lưu đồ thuật toán ScreenTranslator

Dưới đây là lưu đồ tái hiện quy trình hoạt động của code trong folder này.

```mermaid
graph TD
    A[Bắt đầu] --> B{Nhấn Alt+Q?}
    B -- Có --> C[Hiển thị ScreenOverlay]
    C --> D[Người dùng chọn vùng]
    D --> E[Chụp ảnh vùng chọn]
    
    subgraph Core [Xử lý lõi]
        E --> F[Tiền xử lý: Grayscale & Contrast]
        F --> G[Nhận diện chữ (OCR): Tesseract eng+jpn]
        G --> H[Làm sạch văn bản: clean_text & filter_text]
    end

    H --> I{Kiểm tra Cache?}
    I -- Chưa có --> J{Sử dụng API?}
    J -- Có --> K[Langbly API]
    J -- Không --> L[Google Translator]
    
    K --> M[Lưu kết quả vào Cache]
    L --> M
    I -- Đã có --> N[Lấy từ Cache]
    
    M --> O[Hiển thị kết quả lên TooltipWindow]
    N --> O
    
    O --> P[Kết thúc]
```

*Xem chi tiết hơn tại artifact đính kèm.*
