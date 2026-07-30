-- =====================================================================
-- CASMS Supabase PostgreSQL 行級安全策略 (Row Level Security - RLS)
-- =====================================================================
-- 說明：請在 Supabase SQL Editor 中執行此 DDL，以在資料庫層啟用嚴格隔離。

-- 啟用 RLS
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.maintenance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.damage_logs ENABLE ROW LEVEL SECURITY;

-- 輔助函式：獲取當前請求使用者的 email 與 role
CREATE OR REPLACE FUNCTION public.get_current_user_email()
RETURNS text AS $$
  SELECT COALESCE(
    current_setting('request.jwt.claim.email', true),
    ''
  );
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION public.get_current_user_role()
RETURNS text AS $$
  SELECT COALESCE(
    (SELECT role::text FROM public.users WHERE email = public.get_current_user_email()),
    'Employee'
  );
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION public.get_current_user_dept()
RETURNS integer AS $$
  SELECT department_id FROM public.users WHERE email = public.get_current_user_email();
$$ LANGUAGE sql STABLE;


-- ==========================================
-- 1. departments 安全政策
-- ==========================================
CREATE POLICY select_departments ON public.departments
    FOR SELECT TO authenticated
    USING (true);

CREATE POLICY all_departments_admin ON public.departments
    FOR ALL TO authenticated
    USING (public.get_current_user_role() = 'Admin');


-- ==========================================
-- 2. users 安全政策
-- ==========================================
CREATE POLICY select_self_user ON public.users
    FOR SELECT TO authenticated
    USING (email = public.get_current_user_email() OR public.get_current_user_role() = 'Admin');

CREATE POLICY all_users_admin ON public.users
    FOR ALL TO authenticated
    USING (public.get_current_user_role() = 'Admin');


-- ==========================================
-- 3. assets 安全政策
-- ==========================================
-- 一般員工只能讀取同科室資產或公開資產 (department_id IS NULL)
-- Admin 與 Custodian 可讀取全部
CREATE POLICY select_assets ON public.assets
    FOR SELECT TO authenticated
    USING (
        public.get_current_user_role() IN ('Admin', 'Custodian')
        OR department_id IS NULL
        OR department_id = public.get_current_user_dept()
    );

-- 僅 Admin 能新增與管理資產
CREATE POLICY all_assets_admin ON public.assets
    FOR ALL TO authenticated
    USING (public.get_current_user_role() = 'Admin');


-- ==========================================
-- 4. reservations 安全政策
-- ==========================================
-- 一般員工只能查詢與建立自己科室下資產的預約（或讀取自己建立的預約）
CREATE POLICY select_reservations ON public.reservations
    FOR SELECT TO authenticated
    USING (
        public.get_current_user_role() = 'Admin'
        -- 借用者本人
        OR borrower_id = (SELECT id FROM public.users WHERE email = public.get_current_user_email())
        -- 保管人可看自己保管資產的預約
        OR (
            public.get_current_user_role() = 'Custodian'
            AND asset_id IN (SELECT id FROM public.assets WHERE custodian_id = (SELECT id FROM public.users WHERE email = public.get_current_user_email()))
        )
    );

-- 建立預約：一般員工只能預約自己科室或公開的資產
CREATE POLICY insert_reservations ON public.reservations
    FOR INSERT TO authenticated
    WITH CHECK (
        public.get_current_user_role() = 'Admin'
        OR asset_id IN (
            SELECT id FROM public.assets 
            WHERE department_id IS NULL OR department_id = public.get_current_user_dept()
        )
    );

-- 審核預約與歸還：保管人只能更新自己保管資產的預約，Admin 可更新全部
CREATE POLICY update_reservations ON public.reservations
    FOR UPDATE TO authenticated
    USING (
        public.get_current_user_role() = 'Admin'
        OR (
            public.get_current_user_role() = 'Custodian'
            AND asset_id IN (
                SELECT id FROM public.assets 
                WHERE custodian_id = (SELECT id FROM public.users WHERE email = public.get_current_user_email())
            )
        )
    );


-- ==========================================
-- 5. damage_logs 安全政策
-- ==========================================
-- 僅 Admin 與保管人可以讀取或寫入損壞日誌
CREATE POLICY all_damage_logs ON public.damage_logs
    FOR ALL TO authenticated
    USING (
        public.get_current_user_role() = 'Admin'
        OR (
            public.get_current_user_role() = 'Custodian'
            AND asset_id IN (
                SELECT id FROM public.assets 
                WHERE custodian_id = (SELECT id FROM public.users WHERE email = public.get_current_user_email())
            )
        )
    );


-- ==========================================
-- 6. maintenance_records 安全政策
-- ==========================================
-- 僅 Admin 與保管人可以查詢或寫入維修紀錄
CREATE POLICY all_maintenance_records ON public.maintenance_records
    FOR ALL TO authenticated
    USING (
        public.get_current_user_role() = 'Admin'
        OR (
            public.get_current_user_role() = 'Custodian'
            AND asset_id IN (
                SELECT id FROM public.assets 
                WHERE custodian_id = (SELECT id FROM public.users WHERE email = public.get_current_user_email())
            )
        )
    );
