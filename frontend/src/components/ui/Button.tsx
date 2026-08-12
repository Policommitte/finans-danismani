import React from 'react';

type ButtonProps = {
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary';
};

export default function Button({ children, onClick, variant = 'primary' }: ButtonProps) {
  const style = {
    padding: '8px 16px',
    borderRadius: 6,
    border: 'none',
    cursor: 'pointer',
    fontWeight: 600,
    background: variant === 'primary' ? '#3b82f6' : '#e5e7eb',
    color: variant === 'primary' ? '#fff' : '#111827',
  };

  return (
    <button style={style} onClick={onClick}>
      {children}
    </button>
  );
}  