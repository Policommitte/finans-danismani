import { useState } from 'react';
import Layout from '../components/Layout';
import Card from '../components/ui/Card';
import { Button } from '../components/ui/Button';

type Mesaj = {
  id: number;
  rol: 'kullanici' | 'asistan';
  icerik: string;
};

const ilkMesajlar: Mesaj[] = [
  { id: 1, rol: 'asistan', icerik: 'Merhaba! Portföyünüz ve piyasa hakkında sorularınızı yanıtlayabilirim.' },
];

export default function AIChat() {
  const [mesajlar, setMesajlar] = useState<Mesaj[]>(ilkMesajlar);
  const [input, setInput] = useState('');
  const [yaziyor, setYaziyor] = useState(false);

  const mesajGonder = () => {
    if (!input.trim()) return;

    const yeniMesaj: Mesaj = { id: Date.now(), rol: 'kullanici', icerik: input };
    setMesajlar((prev) => [...prev, yeniMesaj]);
    setInput('');
    setYaziyor(true);

    setTimeout(() => {
      setMesajlar((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          rol: 'asistan',
          icerik: 'Bu bir mock yanıttır. Backend entegrasyonu tamamlanınca gerçek AI yanıtları burada görünecek.',
        },
      ]);
      setYaziyor(false);
    }, 1000);
  };

  return (
    <Layout>
      <h1>AI Chat</h1>
      <p>Finansal danışmanınıza sorularınızı sorun.</p>

      <Card title="">
        <div style={{ display: 'flex', flexDirection: 'column', height: 400 }}>
          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
            {mesajlar.map((m) => (
              <div
                key={m.id}
                style={{
                  alignSelf: m.rol === 'kullanici' ? 'flex-end' : 'flex-start',
                  background: m.rol === 'kullanici' ? '#3b82f6' : '#f3f4f6',
                  color: m.rol === 'kullanici' ? '#fff' : '#111827',
                  padding: '8px 12px',
                  borderRadius: 12,
                  maxWidth: '70%',
                  fontSize: 14,
                }}
              >
                {m.icerik}
              </div>
            ))}
            {yaziyor && (
              <div style={{ alignSelf: 'flex-start', color: '#9ca3af', fontSize: 13 }}>
                Asistan yazıyor...
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && mesajGonder()}
              placeholder="Mesajınızı yazın..."
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 8,
                border: '1px solid #d1d5db',
                fontSize: 14,
              }}
            />
            <Button onClick={mesajGonder}>Gönder</Button>
          </div>
        </div>
      </Card>
    </Layout>
  );
}