# Nền tảng Phân tích Dữ liệu AI (HITL)

Hệ thống phân tích dữ liệu theo kiến trúc **Multi-Agent Supervisor** và **Human-in-the-loop**.
Toàn bộ giao diện, phản hồi API và phản hồi agent đều bằng tiếng Việt.

## Cấu trúc thư mục

```
new_app/
├── backend/
│   ├── main.py
│   ├── graph.py
│   ├── agents/
│   ├── services/
│   ├── database/
│   └── utils/
├── frontend/
│   └── app.py
├── requirements.txt
├── .env.example
└── README.md
```

## Cài đặt

```bash
cd new_app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Cập nhật `.env` với `OPENAI_API_KEY` hợp lệ. Có thể dùng model riêng cho sinh mã:

```bash
OPENAI_MODEL=gpt-5-mini
OPENAI_CODE_MODEL=gpt-5.3-codex
```

`OPENAI_MODEL` dùng cho supervisor/analyst. `OPENAI_CODE_MODEL` dùng riêng cho code generator; nếu tài khoản chưa có model này, đổi sang model coding mạnh nhất mà tài khoản hỗ trợ.

## Chạy backend

```bash
cd new_app
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Chạy frontend

```bash
cd new_app
streamlit run frontend/app.py
```

## Luồng sử dụng

1. Tải nhiều file CSV.
2. Trò chuyện hoặc yêu cầu tạo mã.
3. Xem và chỉnh sửa mã sinh ra.
4. Phê duyệt và thực thi.
5. Xem biểu đồ, bảng kết quả và nhận định.

## Ghi chú bảo mật

- Code chỉ được thực thi sau khi người dùng phê duyệt.
- Sandbox hạn chế import và truy cập hệ thống.
- Không cho phép thao tác mạng hay hệ thống trong mã phân tích.
- Code sinh ra được kiểm tra tĩnh và tự sửa trước khi hiển thị để giảm lỗi cú pháp, thiếu `result`, placeholder và import nguy hiểm.
