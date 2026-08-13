import { Link } from 'react-router-dom';

export default function Sidebar() {
  return (
    <nav>
      <div><Link to="/">Dashboard</Link></div>
      <div><Link to="/portfoy">Portföy</Link></div>
      <div><Link to="/piyasa">Piyasa</Link></div>
      <div><Link to="/risk">Risk</Link></div>
      <div><Link to="/ai-chat">AI Chat</Link></div>
    </nav>
  );
}
