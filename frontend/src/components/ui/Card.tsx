import React from 'react';

type CardProps = {
  title?: string;
  children: React.ReactNode;
};

export default function Card({ title, children }: CardProps) {
  return (
    <div
      style={{
        border: '1px solid #e5e7eb',
        borderRadius: 10,
        padding: 16,
        marginBottom: 16,
      }}
    >
      {title && <h3 style={{ marginTop: 0 }}>{title}</h3>}
      {children}
    </div>
  );
}
