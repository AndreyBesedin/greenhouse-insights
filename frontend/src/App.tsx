import { Route, Routes } from 'react-router-dom'

import { RequireSession, SessionProvider } from './auth/SessionProvider'
import { GreenhouseDashboardPage } from './pages/GreenhouseDashboardPage'
import { GreenhouseListPage } from './pages/GreenhouseListPage'
import { LoginPage } from './pages/LoginPage'
import { NewGreenhousePage } from './pages/NewGreenhousePage'

function App() {
  return (
    <SessionProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <RequireSession>
              <GreenhouseListPage />
            </RequireSession>
          }
        />
        <Route
          path="/greenhouses/new"
          element={
            <RequireSession>
              <NewGreenhousePage />
            </RequireSession>
          }
        />
        <Route
          path="/greenhouses/:greenhouseId"
          element={
            <RequireSession>
              <GreenhouseDashboardPage />
            </RequireSession>
          }
        />
      </Routes>
    </SessionProvider>
  )
}

export default App
