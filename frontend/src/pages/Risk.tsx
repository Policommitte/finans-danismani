import Layout from '../components/Layout';
import Card from '../components/ui/Card';

const mockRisk = {
  guncelSkor: 7.5,
  hedefSkor: 5.0,
  uyumlu: false,
  aciliyet: 'Yüksek',
  oneriler: [
    { varlik: 'Hisse Senedi Fonu (TI3)', aksiyon: 'Sat', tutar: 15000 },
    { varlik: 'Altın (XAU/TRY)', aksiyon: 'Al', tutar: 15000 },
  ],
  ozet: 'Portföy riskiniz "Orta" seviye hedefinizin üzerine çıkmıştır. Altın ağırliğini artirmanizi öneriyoruz.',
};

export default function Risk() {
  const skorYuzde = (mockRisk.guncelSkor / 10) * 100;

  return (
    <Layout>
      <h1>Risk</h1>
      <p>Risk skorunuz ve strateji önerileri.</p>

      <Card title="Risk Skoru">
        <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>Güncel Skor</div>
            <div style={{ fontSize: 32, fontWeight: 700, color: '#dc2626' }}>{mockRisk.guncelSkor}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>Hedef Skor</div>
            <div style={{ fontSize: 32, fontWeight: 700, color: '#059669' }}>{mockRisk.hedefSkor}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>Aciliyet</div>
            <div style={{ fontSize: 16, fontWeight: 600, color: '#dc2626' }}>{mockRisk.aciliyet}</div>
          </div>
        </div>

        <div style={{ width: '100%', height: 12, background: '#f3f4f6', borderRadius: 6, overflow: 'hidden', marginBottom: 16 }}>
          <div style={{ width: `${skorYuzde}%`, height: '100%', background: '#dc2626' }} />
        </div>

        <p style={{ fontSize: 14, color: '#374151' }}>{mockRisk.ozet}</p>
      </Card>

      <Card title="Yeniden Dengeleme Önerileri">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ padding: '8px 4px' }}>Varlık</th>
              <th style={{ padding: '8px 4px' }}>Aksiyon</th>
              <th style={{ padding: '8px 4px', textAlign: 'right' }}>Tutar</th>
            </tr>
          </thead>
          <tbody>
            {mockRisk.oneriler.map((o, i) => (
              <tr key={i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{ padding: '8px 4px' }}>{o.varlik}</td>
                <td style={{ padding: '8px 4px', fontWeight: 600, color: o.aksiyon === 'Sat' ? '#dc2626' : '#059669' }}>
                  {o.aksiyon}
                </td>
                <td style={{ padding: '8px 4px', textAlign: 'right' }}>{o.tutar.toLocaleString('tr-TR')} ₺</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={{ fontSize: 12, color: '#9ca3af', marginTop: 12 }}>
          Bu bir yatirim tavsiyesi değildir.
        </p>
      </Card>
    </Layout>
  );
}