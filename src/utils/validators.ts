import type { RegisterFormState } from '@/types/auth';

export class RegisterValidator {
  static validate(form: RegisterFormState): string | null {
    if (!form.username || form.username.length < 3) {
      return '使用者名稱至少需要 3 個字元';
    }
    if (!form.password || form.password.length < 6) {
      return '密碼至少需要 6 個字元';
    }
    if (form.password !== form.confirmPassword) {
      return '兩次輸入的密碼不一致';
    }
    return null;
  }
}
