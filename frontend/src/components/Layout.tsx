import React from 'react';

import Sidebar from './Sidebar';

type LayoutProps = {
 children: React.ReactNode;
};

export default function Layout({ children }: LayoutProps) {
 return (
 <div style={{ display: 'flex' }}>
 <Sidebar />
 <main style={{ flex: 1, padding: 20 }}>{children}</main>
 </div>
 );
}

