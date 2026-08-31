import { Route, Routes } from 'react-router-dom'

import { GreenhouseDashboardPage } from './pages/GreenhouseDashboardPage'
import { GreenhouseListPage } from './pages/GreenhouseListPage'
import { LoginPage } from './pages/LoginPage'
import { NewGreenhousePage } from './pages/NewGreenhousePage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<GreenhouseListPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/greenhouses/new" element={<NewGreenhousePage />} />
      <Route path="/greenhouses/:greenhouseId" element={<GreenhouseDashboardPage />} />
    </Routes>
  )
}

export default App
