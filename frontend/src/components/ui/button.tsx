import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-[10px] text-sm font-bold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fuchsia-300 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'brand-button',
        secondary: 'bg-fuchsia-50 text-fuchsia-800 hover:bg-fuchsia-100',
        outline: 'border border-slate-200 bg-white text-slate-700 hover:border-fuchsia-200 hover:bg-fuchsia-50 hover:text-fuchsia-800',
        ghost: 'text-slate-600 hover:bg-fuchsia-50 hover:text-fuchsia-800',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-md px-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, ...props }, ref) => (
  <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
));
Button.displayName = 'Button';
