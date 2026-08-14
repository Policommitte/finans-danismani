import Layout from '../components/Layout';
import Card from '../components/ui/Card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

type PiyasaOzet = {
  sembol: string;
  ad: string;
  fiyat: number;
  degisimYuzde: number;
};

const mockPiyasaOzet: PiyasaOzet[] = [
  { sembol: 'THYAO', ad: 'Türk Hava Yolları', fiyat: 312, degisimYuzde: 2.4 },
  { sembol: 'XAU', ad: 'Altın (gram)', fiyat: 2650, degisimYuzde: 0.8 },
  { sembol: 'USDTRY', ad: 'Dolar/TL', fiyat: 34.8, degisimYuzde: -0.3 },
  { sembol: 'BIST100', ad: 'BIST 100 Endeksi', fiyat: 9850, degisimYuzde: 1.1 },
];

const mockFiyatGecmisi = [
  { gun: 'Pzt', fiyat: 298 },
  { gun: 'Sal', fiyat: 302 },
  { gun: 'Çar', fiyat: 295 },
  { gun: 'Per', fiyat: 305 },
  { gun: 'Cum', fiyat: 312 },
];

export default function Market() {
  return (
    <Layout>
      <h1>Piyasa</h1>
      <p>Güncel piyasa verileri ve fiyat hareketleri.</p>

      <Card title="Piyasa Özeti">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
          {mockPiyasaOzet.map((p) => {
            const pozitif = p.degisimYuzde >= 0;
            return (
              <div key={p.sembol} style={{ background: '#f9fafb', borderRadius: 8, padding: 12 }}>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{p.ad}</div>
                <div style={{ fontSize: 18, fontWeight: 700 }}>{p.fiyat.toLocaleString('tr-TR')}</div>
                <div style={{ fontSize: 13, color: pozitif ? '#059669' : '#dc2626', fontWeight: 600 }}>
                  {pozitif ? '▲' : '▼'} %{Math.abs(p.degisimYuzde)}
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <Card title="THYAO - Son 5 Gün">
        <div style={{ width: '100%', height: 280 }}>
          <ResponsiveContainer>
            <LineChart data={mockFiyatGecmisi}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="gun" />
              <YAxis domain={['dataMin - 10', 'dataMax + 10']} />
              <Tooltip />
              <Line type="monotone" dataKey="fiyat" stroke="#10B981" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </Layout>
  );
}