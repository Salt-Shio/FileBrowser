export type ComponentSize = 'sm' | 'md' | 'lg';
export type ComponentVariant = 'default' | 'primary' | 'secondary' | 'ghost' | 'outline' | 'white';

export interface BaseInputProps {
  modelValue: string;
  type?: 'text' | 'password' | 'email';
  placeholder?: string;
  label?: string;
  disabled?: boolean;
  variant?: ComponentVariant;
}

export interface BaseButtonProps {
  variant?: ComponentVariant;
  disabled?: boolean;
  loading?: boolean;
}
