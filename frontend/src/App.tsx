import { Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import Market from './pages/Market';
import Risk from './pages/Risk';
import AIChat from './pages/AIChat';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/portfoy" element={<Portfolio />} />
      <Route path="/piyasa" element={<Market />} />
      <Route path="/risk" element={<Risk />} />
      <Route path="/ai-chat" element={<AIChat />} />
    </Routes>
  );
}

export default App;

