import { ButtonHTMLAttributes, forwardRef } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger'
}

const variants: Record<string, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700',
  secondary: 'bg-slate-700 text-slate-200 hover:bg-slate-600 border border-slate-600',
  danger: 'bg-red-600 text-white hover:bg-red-700',
}

export const Button = forwardRef<HTMLButtonElement, Props>(
  ({ variant = 'primary', className = '', children, ...rest }, ref) => (
    <button
      ref={ref}
      className={`px-4 py-2 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      {...rest}
    >
      {children}
    </button>
  ),
)
Button.displayName = 'Button'
