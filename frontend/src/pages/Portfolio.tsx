import Layout from '../components/Layout';
import Card from '../components/ui/Card';

type Varlik = {
  sembol: string;
  ad: string;
  tur: string;
  miktar: number;
  ortalamaFiyat: number;
  guncelFiyat: number;
};

const mockVarliklar: Varlik[] = [
  { sembol: 'THYAO', ad: 'Türk Hava Yolları', tur: 'Hisse', miktar: 100, ortalamaFiyat: 280, guncelFiyat: 312 },
  { sembol: 'XAU', ad: 'Altın', tur: 'Emtia', miktar: 30, ortalamaFiyat: 2400, guncelFiyat: 2650 },
  { sembol: 'USD', ad: 'Amerikan Doları', tur: 'Döviz', miktar: 500, ortalamaFiyat: 34.2, guncelFiyat: 34.8 },
  { sembol: 'AFT', ad: 'Karma Fon', tur: 'Fon', miktar: 200, ortalamaFiyat: 12.5, guncelFiyat: 13.1 },
];

export default function Portfolio() {
  return (
    <Layout>
      <h1>Portföy</h1>
      <p>Elinizdeki varlıkların detaylı listesi.</p>

      <Card title="Varlık Listesi">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ padding: '8px 4px' }}>Sembol</th>
              <th style={{ padding: '8px 4px' }}>Ad</th>
              <th style={{ padding: '8px 4px' }}>Tür</th>
              <th style={{ padding: '8px 4px', textAlign: 'right' }}>Miktar</th>
              <th style={{ padding: '8px 4px', textAlign: 'right' }}>Ort. Fiyat</th>
              <th style={{ padding: '8px 4px', textAlign: 'right' }}>Güncel Fiyat</th>
              <th style={{ padding: '8px 4px', textAlign: 'right' }}>Kâr/Zarar</th>
            </tr>
          </thead>
          <tbody>
            {mockVarliklar.map((v) => {
              const karZarar = ((v.guncelFiyat - v.ortalamaFiyat) / v.ortalamaFiyat) * 100;
              const pozitif = karZarar >= 0;
              return (
                <tr key={v.sembol} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={{ padding: '8px 4px', fontWeight: 600 }}>{v.sembol}</td>
                  <td style={{ padding: '8px 4px' }}>{v.ad}</td>
                  <td style={{ padding: '8px 4px', color: '#6b7280' }}>{v.tur}</td>
                  <td style={{ padding: '8px 4px', textAlign: 'right' }}>{v.miktar}</td>
                  <td style={{ padding: '8px 4px', textAlign: 'right' }}>{v.ortalamaFiyat.toLocaleString('tr-TR')} ₺</td>
                  <td style={{ padding: '8px 4px', textAlign: 'right' }}>{v.guncelFiyat.toLocaleString('tr-TR')} ₺</td>
                  <td style={{ padding: '8px 4px', textAlign: 'right', color: pozitif ? '#059669' : '#dc2626', fontWeight: 600 }}>
                    {pozitif ? '▲' : '▼'} %{Math.abs(karZarar).toFixed(1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </Layout>
  );
}