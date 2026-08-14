import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import Card from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import PortfolioPieChart from '../components/PortfolioPieChart';
import { api } from '../api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const mockData = [
  { ay: 'Ocak', deger: 1000 },
  { ay: 'Şubat', deger: 1200 },
  { ay: 'Mart', deger: 900 },
  { ay: 'Nisan', deger: 1500 },
  { ay: 'Mayıs', deger: 1300 },
  { ay: 'Haziran', deger: 1700 },
];

export default function Dashboard() {
  const [health, setHealth] = useState<string>('kontrol ediliyor...');

  useEffect(() => {
    api.getHealth().then((res) => {
      setHealth(`${res.status} (${res.source})`);
    });
  }, []);

  return (
    <Layout>
      <h1>Dashboard</h1>
      <p>Backend durumu: <strong>{health}</strong></p>

      <Card title="">
        <PortfolioPieChart />
      </Card>

      <Card title="Örnek Kart">
        <p>Bu bir Card bileşeni içinde gösterilen içerik.</p>
        <Button onClick={() => alert('Butona tıklandı!')}>Tıkla</Button>
      </Card>

      <Card title="Portföy Değeri (mock veri)">
        <div style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer>
            <LineChart data={mockData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="ay" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="deger" stroke="#3b82f6" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </Layout>
  );
}