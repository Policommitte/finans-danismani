import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PieChart, Pie, Cell, LabelList, Tooltip, ResponsiveContainer, Sector,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import Badge from './ui/Badge';

type AssetSlice = {
  tur: string;
  miktar: number;
  deger: number;
  yuzde: number;
};

type Kur = 'TRY' | 'EUR' | 'USD';
type Gorunum = 'pasta' | 'sutun';
type ZamanAraligi = '1g' | '1h' | '1a' | '1y' | 'tumu';

const mockPortfolio: AssetSlice[] = [
  { tur: 'Hisse Senedi', miktar: 120, deger: 45000, yuzde: 45 },
  { tur: 'Altin', miktar: 30, deger: 25000, yuzde: 25 },
  { tur: 'DÃ¶viz', miktar: 500, deger: 20000, yuzde: 20 },
  { tur: 'Fon', miktar: 15, deger: 10000, yuzde: 10 },
];

const mockGecmisVeri: Record<ZamanAraligi, { etiket: string; deger: number }[]> = {
  '1g': [
    { etiket: '09:00', deger: 98500 }, { etiket: '12:00', deger: 99200 },
    { etiket: '15:00', deger: 99800 }, { etiket: '18:00', deger: 100000 },
  ],
  '1h': [
    { etiket: 'Pzt', deger: 96000 }, { etiket: 'Sal', deger: 97500 },
    { etiket: 'Ã‡ar', deger: 96800 }, { etiket: 'Per', deger: 98200 },
    { etiket: 'Cum', deger: 100000 },
  ],
  '1a': [
    { etiket: 'Hafta 1', deger: 90000 }, { etiket: 'Hafta 2', deger: 93500 },
    { etiket: 'Hafta 3', deger: 97000 }, { etiket: 'Hafta 4', deger: 100000 },
  ],
  '1y': [
    { etiket: 'Ocak', deger: 70000 }, { etiket: 'Mart', deger: 78000 },
    { etiket: 'MayÄ±s', deger: 85000 }, { etiket: 'Temmuz', deger: 91000 },
    { etiket: 'EylÃ¼l', deger: 95000 }, { etiket: 'KasÄ±m', deger: 100000 },
  ],
  tumu: [
    { etiket: '2023', deger: 40000 }, { etiket: '2024', deger: 65000 },
    { etiket: '2025', deger: 85000 }, { etiket: '2026', deger: 100000 },
  ],
};

const ZAMAN_ETIKET: Record<ZamanAraligi, string> = {
  '1g': '1 GÃ¼n', '1h': '1 Hafta', '1a': '1 Ay', '1y': '1 YÄ±l', tumu: 'TÃ¼mÃ¼',
};

const KUR_ORANLARI: Record<Kur, number> = { TRY: 1, EUR: 0.027, USD: 0.029 };
const KUR_SEMBOL: Record<Kur, string> = { TRY: 'â‚º', EUR: 'â‚¬', USD: '$' };
const MAT_RENKLER = ['#3B82F6', '#10B981', '#8B5CF6', '#06B6D4'];

function renderActiveShape(props: any) {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
  return (
    <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius + 10}
      startAngle={startAngle} endAngle={endAngle} fill={fill} cornerRadius={8} />
  );
}

export default function PortfolioPieChart() {
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);
  const [kur, setKur] = useState<Kur>('TRY');
  const [gorunum, setGorunum] = useState<Gorunum>('pasta');
  const [zamanAraligi, setZamanAraligi] = useState<ZamanAraligi>('1a');
  const [veriHatasi, setVeriHatasi] = useState(false);
  const navigate = useNavigate();

  const cevir = (tutar: number) => tutar * KUR_ORANLARI[kur];
  const toplamVarlik = mockPortfolio.reduce((sum, item) => sum + cevir(item.deger), 0);
  const gecmisVeri = mockGecmisVeri[zamanAraligi];

  const sutunGorunumeGec = () => {
    // GerÃ§ek backend baÄŸlanÄ±nca burada veri Ã§ekme hatasÄ± kontrolÃ¼ yapÄ±lacak
    if (!gecmisVeri || gecmisVeri.length === 0) {
      setVeriHatasi(true);
      setTimeout(() => {
        setVeriHatasi(false);
        setGorunum('pasta');
      }, 1500);
      return;
    }
    setGorunum('sutun');
  };

  return (
    <div className="flex flex-col rounded-xl border border-gray-200 bg-white shadow-sm">
      <style>{`
        @keyframes spinIn {
          from { transform: rotate(-180deg) scale(0.7); opacity: 0; }
          to { transform: rotate(0deg) scale(1); opacity: 1; }
        }
        .pie-spin-in { animation: spinIn 0.8s ease-out; }
      `}</style>

      <div className="flex items-center justify-between px-6 pt-6">
        <div>
          <div className="flex items-center gap-2 text-lg font-semibold">
            PortfÃ¶y {gorunum === 'pasta' ? 'DaÄŸÄ±lÄ±mÄ±' : 'PerformansÄ±'}
            <Badge className="bg-green-100 text-green-700">
              <span>â–² 5.2%</span>
            </Badge>
          </div>
          <div className="mt-2 flex gap-1">
            <button
              onClick={() => setGorunum('pasta')}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                gorunum === 'pasta' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Pasta Grafik
            </button>
            <button
              onClick={sutunGorunumeGec}
              className={`rounded-md px-3 py-1 text-xs font-medium ${
                gorunum === 'sutun' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              SÃ¼tun Grafik
            </button>
          </div>
        </div>
        <div className="text-right">
          <div className="mb-1 flex justify-end gap-1">
            {(['TRY', 'EUR', 'USD'] as Kur[]).map((k) => (
              <button
                key={k}
                onClick={() => setKur(k)}
                className={`rounded-md px-2 py-1 text-xs font-medium ${
                  kur === k ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {k}
              </button>
            ))}
          </div>
          <div className="text-xs text-gray-500">Toplam VarlÄ±k</div>
          <div className="text-xl font-bold">
            {toplamVarlik.toLocaleString('tr-TR', { maximumFractionDigits: 2 })} {KUR_SEMBOL[kur]}
          </div>
        </div>
      </div>

      {veriHatasi && (
        <div className="mx-6 mt-4 rounded-md bg-amber-50 px-4 py-2 text-sm text-amber-700">
          GeÃ§miÅŸ veriye ulaÅŸÄ±lamadÄ±, pasta grafiÄŸe dÃ¶nÃ¼lÃ¼yor...
        </div>
      )}

      {gorunum === 'pasta' && (
        <div className="px-2 pb-4">
          <div className="pie-spin-in" style={{ width: '100%', height: 320 }}>
            <ResponsiveContainer>
              <PieChart>
                <Tooltip
                  formatter={(value: number, name: string, props: any) => [
                    `${cevir(props.payload.deger).toLocaleString('tr-TR', { maximumFractionDigits: 2 })} ${KUR_SEMBOL[kur]} (${props.payload.miktar} adet)`,
                    name,
                  ]}
                />
                <Pie
                  data={mockPortfolio}
                  dataKey="deger"
                  nameKey="tur"
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={110}
                  cornerRadius={8}
                  paddingAngle={4}
                  activeIndex={activeIndex}
                  activeShape={renderActiveShape}
                  onClick={() => navigate('/portfoy')}
                >
                  {mockPortfolio.map((_, index) => (
                    <Cell
                      key={index}
                      fill={MAT_RENKLER[index % MAT_RENKLER.length]}
                      stroke="none"
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={() => setActiveIndex(index)}
                      onMouseLeave={() => setActiveIndex(undefined)}
                    />
                  ))}
                  <LabelList
                    dataKey="yuzde"
                    stroke="none"
                    fontSize={12}
                    fontWeight={500}
                    fill="#fff"
                    formatter={(value: number) => `%${value}`}
                  />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {gorunum === 'sutun' && (
        <div className="px-6 pb-6">
          <div className="mb-3 flex gap-1">
            {(Object.keys(ZAMAN_ETIKET) as ZamanAraligi[]).map((z) => (
              <button
                key={z}
                onClick={() => setZamanAraligi(z)}
                className={`rounded-md px-2 py-1 text-xs font-medium ${
                  zamanAraligi === z ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {ZAMAN_ETIKET[z]}
              </button>
            ))}
          </div>

          <div className="flex gap-4">
            <div style={{ width: '65%', height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={gecmisVeri}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="etiket" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip
                    formatter={(value: number) => [
                      `${cevir(value).toLocaleString('tr-TR', { maximumFractionDigits: 2 })} ${KUR_SEMBOL[kur]}`,
                      'DeÄŸer',
                    ]}
                  />
                  <Bar dataKey="deger" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex-1 space-y-2 text-sm">
              {(Object.keys(ZAMAN_ETIKET) as ZamanAraligi[]).map((z, i) => {
                const veri = mockGecmisVeri[z];
                const ilk = veri[0].deger;
                const son = veri[veri.length - 1].deger;
                const degisimYuzde = ((son - ilk) / ilk) * 100;
                const pozitif = degisimYuzde >= 0;
                return (
                  <div
                    key={z}
                    className={`flex items-center justify-between rounded-md px-3 py-2 ${
                      pozitif ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                    }`}
                  >
                    <span className="font-medium">{ZAMAN_ETIKET[z]}</span>
                    <span>{pozitif ? '\u25B2' : '\u25BC'} %{Math.abs(degisimYuzde).toFixed(1)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}   