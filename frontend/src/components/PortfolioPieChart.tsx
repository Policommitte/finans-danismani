import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PieChart, Pie, Cell, LabelList, Tooltip, ResponsiveContainer, Sector,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts';
import Badge from './ui/Badge';

type AssetSlice = {
  type: string;
  quantity: number;
  value: number;
  percent: number;
};

type Currency = 'TRY' | 'EUR' | 'USD';
type ViewMode = 'pie' | 'bar';
type TimeRange = '1d' | '1w' | '1m' | '1y' | 'all';

const mockPortfolio: AssetSlice[] = [
  { type: 'Stocks', quantity: 120, value: 45000, percent: 45 },
  { type: 'Gold', quantity: 30, value: 25000, percent: 25 },
  { type: 'Currency', quantity: 500, value: 20000, percent: 20 },
  { type: 'Fund', quantity: 15, value: 10000, percent: 10 },
];

const mockHistory: Record<TimeRange, { label: string; value: number }[]> = {
  '1d': [
    { label: '09:00', value: 98500 }, { label: '12:00', value: 99200 },
    { label: '15:00', value: 99800 }, { label: '18:00', value: 100000 },
  ],
  '1w': [
    { label: 'Mon', value: 96000 }, { label: 'Tue', value: 97500 },
    { label: 'Wed', value: 96800 }, { label: 'Thu', value: 98200 },
    { label: 'Fri', value: 100000 },
  ],
  '1m': [
    { label: 'Week 1', value: 90000 }, { label: 'Week 2', value: 93500 },
    { label: 'Week 3', value: 97000 }, { label: 'Week 4', value: 100000 },
  ],
  '1y': [
    { label: 'Jan', value: 70000 }, { label: 'Mar', value: 78000 },
    { label: 'May', value: 85000 }, { label: 'Jul', value: 91000 },
    { label: 'Sep', value: 95000 }, { label: 'Nov', value: 100000 },
  ],
  all: [
    { label: '2023', value: 40000 }, { label: '2024', value: 65000 },
    { label: '2025', value: 85000 }, { label: '2026', value: 100000 },
  ],
};

const RANGE_LABEL: Record<TimeRange, string> = {
  '1d': '1 Day', '1w': '1 Week', '1m': '1 Month', '1y': '1 Year', all: 'All Time',
};

const RATES: Record<Currency, number> = { TRY: 1, EUR: 0.027, USD: 0.029 };
const SYMBOL: Record<Currency, string> = { TRY: 'TL', EUR: '€', USD: '$' };
const COLORS = ['#3B82F6', '#10B981', '#8B5CF6', '#06B6D4'];

function renderActiveShape(props: any) {
  const { cx, cy, innerRadius, outerRadius, startAngle, endAngle, fill } = props;
  return (
    <Sector cx={cx} cy={cy} innerRadius={innerRadius} outerRadius={outerRadius + 10}
      startAngle={startAngle} endAngle={endAngle} fill={fill} />
  );
}

export default function PortfolioPieChart() {
  const [activeIndex, setActiveIndex] = useState<number | undefined>(undefined);
  const [currency, setCurrency] = useState<Currency>('TRY');
  const [view, setView] = useState<ViewMode>('pie');
  const [range, setRange] = useState<TimeRange>('1m');
  const [dataError, setDataError] = useState(false);
  const navigate = useNavigate();

  const convert = (amount: number) => amount * RATES[currency];
  const totalValue = mockPortfolio.reduce((sum, item) => sum + convert(item.value), 0);
  const historyData = mockHistory[range];

  const switchToBarView = () => {
    if (!historyData || historyData.length === 0) {
      setDataError(true);
      setTimeout(() => {
        setDataError(false);
        setView('pie');
      }, 1500);
      return;
    }
    setView('bar');
  };

  return (
    <div className="flex flex-col rounded-none border border-gray-200 bg-white shadow-sm">
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
            Portfolio {view === 'pie' ? 'Allocation' : 'Performance'}
            <Badge className="rounded-none bg-green-100 text-green-700">
              <span>▲ 5.2%</span>
            </Badge>
          </div>
          <div className="mt-2 flex gap-1">
            <button
              onClick={() => setView('pie')}
              className={`rounded-none px-3 py-1 text-xs font-medium ${
                view === 'pie' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Pie Chart
            </button>
            <button
              onClick={switchToBarView}
              className={`rounded-none px-3 py-1 text-xs font-medium ${
                view === 'bar' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              Bar Chart
            </button>
          </div>
        </div>
        <div className="text-right">
          <div className="mb-1 flex justify-end gap-1">
            {(['TRY', 'EUR', 'USD'] as Currency[]).map((c) => (
              <button
                key={c}
                onClick={() => setCurrency(c)}
                className={`rounded-none px-2 py-1 text-xs font-medium ${
                  currency === c ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {c}
              </button>
            ))}
          </div>
          <div className="text-xs text-gray-500">Total Assets</div>
          <div className="text-xl font-bold">
            {totalValue.toLocaleString('en-US', { maximumFractionDigits: 2 })} {SYMBOL[currency]}
          </div>
        </div>
      </div>

      {dataError && (
        <div className="mx-6 mt-4 rounded-none bg-amber-50 px-4 py-2 text-sm text-amber-700">
          Could not load historical data, returning to pie chart...
        </div>
      )}

      {view === 'pie' && (
        <div className="px-2 pb-4">
          <div className="pie-spin-in" style={{ width: '100%', height: 320 }}>
            <ResponsiveContainer>
              <PieChart>
                <Tooltip
                  formatter={(value: number, name: string, props: any) => [
                    `${convert(props.payload.value).toLocaleString('en-US', { maximumFractionDigits: 2 })} ${SYMBOL[currency]} (${props.payload.quantity} units)`,
                    name,
                  ]}
                />
                <Pie
                  data={mockPortfolio}
                  dataKey="value"
                  nameKey="type"
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={110}
                  paddingAngle={4}
                  activeIndex={activeIndex}
                  activeShape={renderActiveShape}
                  onClick={() => navigate('/portfoy')}
                >
                  {mockPortfolio.map((_, index) => (
                    <Cell
                      key={index}
                      fill={COLORS[index % COLORS.length]}
                      stroke="none"
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={() => setActiveIndex(index)}
                      onMouseLeave={() => setActiveIndex(undefined)}
                    />
                  ))}
                  <LabelList
                    dataKey="percent"
                    stroke="none"
                    fontSize={12}
                    fontWeight={500}
                    fill="#fff"
                    formatter={(value: number) => `${value}%`}
                  />
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {view === 'bar' && (
        <div className="px-6 pb-6">
          <div className="mb-3 flex gap-1">
            {(Object.keys(RANGE_LABEL) as TimeRange[]).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`rounded-none px-2 py-1 text-xs font-medium ${
                  range === r ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {RANGE_LABEL[r]}
              </button>
            ))}
          </div>

          <div className="flex gap-4">
            <div style={{ width: '65%', height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={historyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip
                    formatter={(value: number) => [
                      `${convert(value).toLocaleString('en-US', { maximumFractionDigits: 2 })} ${SYMBOL[currency]}`,
                      'Value',
                    ]}
                  />
                  <Bar dataKey="value" fill="#3B82F6" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="flex-1 space-y-2 text-sm">
              {(Object.keys(RANGE_LABEL) as TimeRange[]).map((r) => {
                const data = mockHistory[r];
                const first = data[0].value;
                const last = data[data.length - 1].value;
                const changePercent = ((last - first) / first) * 100;
                const positive = changePercent >= 0;
                return (
                  <div
                    key={r}
                    className={`flex items-center justify-between rounded-none px-3 py-2 ${
                      positive ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                    }`}
                  >
                    <span className="font-medium">{RANGE_LABEL[r]}</span>
                    <span>{positive ? '▲' : '▼'} {Math.abs(changePercent).toFixed(1)}%</span>
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