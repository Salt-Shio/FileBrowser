# Settings & 2FA 功能實作清單

- [x] 1. 安裝 `qrcode.vue` 處理 QRCode 生成
- [x] 2. 更新 `src/api/auth.ts`，封裝 `/2fa/generate`, `/2fa/enable`, `/2fa/disable` 等 API。
- [x] 3. 更新 `src/stores/auth.ts`，擴充 2FA 相關操作狀態管理。
- [x] 4. 實作 `src/components/auth/TwoFactorEnableModal.vue` 元件 (依照 Figma UI 設計)。
- [x] 5. 實作 `src/views/SettingsView.vue` 畫面與互動邏輯 (包含表單與呼叫 Modal)。
- [x] 6. 測試完整的 2FA 啟用流程與後續登入驗證，並等待使用者確認完成。
