import { Route, Routes } from 'react-router-dom'

import { GreenhouseDashboardPage } from './pages/GreenhouseDashboardPage'
import { GreenhouseListPage } from './pages/GreenhouseListPage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<GreenhouseListPage />} />
      <Route path="/greenhouses/:greenhouseId" element={<GreenhouseDashboardPage />} />
    </Routes>
  )
}

export default App
