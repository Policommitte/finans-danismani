import { useState } from 'react';
import { MessageCircle, X } from 'lucide-react';
import { Button } from './ui/Button';
import { cn } from '../lib/utils';

type Mesaj = {
  id: number;
  rol: 'kullanici' | 'asistan';
  icerik: string;
};

const ilkMesajlar: Mesaj[] = [
  { id: 1, rol: 'asistan', icerik: 'Merhaba! Portföyünüz ve piyasa hakkında sorularınızı yanıtlayabilirim.' },
];

export default function FloatingChat() {
  const [acik, setAcik] = useState(false);
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
    <div className="fixed bottom-6 right-6 z-50">
      {acik && (
        <div className="mb-3 w-80 h-[420px] bg-card border border-border shadow-xl flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-primary text-primary-foreground">
            <span className="font-semibold text-sm">AI Chat</span>
            <button onClick={() => setAcik(false)} className="hover:opacity-80">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto flex flex-col gap-2 p-3">
            {mesajlar.map((m) => (
              <div
                key={m.id}
                className={cn(
                  'px-3 py-2 text-sm max-w-[80%]',
                  m.rol === 'kullanici'
                    ? 'self-end bg-primary text-primary-foreground'
                    : 'self-start bg-muted text-muted-foreground'
                )}
              >
                {m.icerik}
              </div>
            ))}
            {yaziyor && (
              <div className="self-start text-xs text-muted-foreground">Asistan yazıyor...</div>
            )}
          </div>

          <div className="flex gap-2 p-3 border-t border-border">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && mesajGonder()}
              placeholder="Mesajınızı yazın..."
              className="flex-1 px-3 py-2 text-sm border border-input bg-background focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <Button size="sm" onClick={mesajGonder}>Gönder</Button>
          </div>
        </div>
      )}

      <button
        onClick={() => setAcik((prev) => !prev)}
        className="h-14 w-14 bg-primary text-primary-foreground shadow-lg flex items-center justify-center hover:bg-primary/90 transition-colors"
      >
        {acik ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>
    </div>
  );
}