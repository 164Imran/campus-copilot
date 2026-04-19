import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Desktop from './components/os/Desktop';
import LandingPage from './scene/LandingPage';
import './styles/globals.css';
import './styles/macos.css';

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/desktop" element={<Desktop />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}

export default App;
