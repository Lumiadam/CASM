# CASMS — 企業級資產與空間管理系統 (MVP)

Corporate Asset & Space Management System：整合 **FastAPI 後端**、**Next.js 儀表板**、**PostgreSQL**、**JWT RBAC** 與 **Docker + Nginx** 單一入口部署，用於展示器材借用、空間預約、設施壽命預警、保管人審核與損壞鎖定等核心流程。

## 專案結構

```
casms/
├── backend/          # FastAPI + SQLAlchemy
├── frontend/         # Next.js 14 App Router + Tailwind
├── deploy/           # Dockerfile、nginx、env 範例
├── docker-compose.yml
└── README.md
```

## 快速啟動（Docker 推薦）

1. 進入專案目錄：

   ```bash
   cd d:\AI技術\casms
   ```

2. （選用）複製環境變數：

   ```bash
   copy deploy\.env.example .env
   ```

3. 建置並啟動全部服務：

   ```bash
   docker-compose up --build
   ```

4. 開啟瀏覽器：

   | 服務 | URL |
   |------|-----|
   | 前端（經 Nginx） | http://localhost |
   | Swagger API 文件 | http://localhost/docs |
   | 健康檢查 | http://localhost/api/health |

Nginx 將 `/api/*` 轉發至後端，其餘路徑轉發至 Next.js。

## 測試帳號

密碼皆為 **`password123`**：

| 角色 | Email | 說明 |
|------|--------|------|
| Admin | admin@casms.local | 可審核任意預約、歸還、維護 |
| Custodian | custodian@casms.local | 僅審核／歸還 **custodian_id 為自己** 的資產 |
| Employee | employee@casms.local | 建立預約、檢視個人借用、可進入各頁檢視 RBAC |

登入頁提供三組快捷帶入按鈕。權限完整對照請見前端 **「權限矩陣」** 頁（`/permissions`）。

## 本地開發（非 Docker）

### 後端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# 未設定 DATABASE_URL 時使用 SQLite ./casms.db
uvicorn app.main:app --reload --port 8000
```

環境變數（選用）：

- `DATABASE_URL` — PostgreSQL 或 SQLite 連線字串
- `SECRET_KEY` — JWT 簽章金鑰
- `SEED_ON_STARTUP=true` — 啟動時寫入種子資料

### 前端

```bash
cd frontend
npm install
set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

瀏覽 http://localhost:3000

## 核心 API 摘要

| 能力 | 端點 |
|------|------|
| 登入 | `POST /auth/login` |
| 權限矩陣 | `GET /permissions/matrix` |
| 資產列表 | `GET /assets?type=DEVICE\|SPACE\|FACILITY` |
| 預約行事曆 | `GET /assets/{id}/calendar` (支援隱私過濾遮蔽) |
| 建立預約 | `POST /reservations`（重疊則 **409**，支援 database 悲觀鎖 `FOR UPDATE`） |
| 保管人核定 | `POST /reservations/{id}/approve` |
| 驗收歸還 | `POST /reservations/{id}/return`（可登記 DamageLog → 連動取消未來預約） |
| 健康檢查 | `GET /health` |

### 核心安全與優化機制

1. **Supabase RLS (Row Level Security) 政策**：
   - 專案在 `deploy/supabase_rls.sql` 中提供了完整的 RLS DDL 政策腳本。
   - 後端 API 落實科室隔離防禦：一般同仁 (Employee) 只能查詢與預約同科室資產或公開資產，無法查詢其他科室的預約行事曆。

2. **JSONB 彈性屬性 Schema**：
   - 移除了資產主表內特定的欄位，改用 `metadata_json` (PostgreSQL `JSONB`) 儲存資產類型的專屬屬性（如設施的安裝日、年限，空間的容納人數等），具備高度架構擴充性。

3. **防重疊預約與悲觀鎖**：
   - 預約寫入時，後端於交易中使用 `with_for_update()` 對資產加鎖，徹底杜絕高併發下的 Race Condition 重複預約漏洞。
   - 同一資產上，若存在 **PENDING** 或 **APPROVED** 預約且 `(T_start < Exist_end) AND (T_end > Exist_start)`，則拒絕新預約。

4. **動態資產狀態計算**：
   - 資產的 `AVAILABLE` 與 `IN_USE` 狀態改由後端動態比對當前時間與已被 `APPROVED` 的預約時段決定。預約核准在預約時間才轉為 `IN_USE`，非預約時間自動回歸 `AVAILABLE`，避免時段鎖定問題。

5. **設施精確壽命與到期日計算**：
   - 後端支援精確跨月與閏年計算，計算預計到期日期，並回傳精確剩餘年限（如：`0.80 年`）與到期日（如：`2027-05-18`）供前端渲染。

6. **器材損壞連帶取消未來預約**：
   - 保管人辦理歸還並登記損壞（狀態改為 `MAINTENANCE`）時，系統將自動連動取消該設備未來所有已核准 (APPROVED) 或待審核 (PENDING) 的預約。

## 技術棧

- **Backend**: FastAPI, SQLAlchemy 2, Pydantic, JWT, bcrypt
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Lucide, next-themes
- **Deploy**: Docker Compose, PostgreSQL 16, Nginx 1.27

## 授權

MVP 展示用途，可依企業需求擴充通知、審計、多租戶等模組。
