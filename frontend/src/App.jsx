import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Auth from './pages/Auth'
import AuthCallback from './pages/AuthCallback'
import Dashboard from './pages/Dashboard'
import CommandCenter from './pages/CommandCenter'
import Home from './components/home'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/auth" element={<Auth />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/project/:id" element={<CommandCenter />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
