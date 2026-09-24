import { Route, Routes } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { AdminPage } from '../features/admin/AdminPage'
import { AdminOverview } from '../features/admin/components/AdminOverview'
import { AuditLogViewer } from '../features/admin/components/AuditLogViewer'
import { UserTable } from '../features/admin/components/UserTable'
import { RoleGuard } from '../features/admin/RoleGuard'
import { ADMIN_ROLES } from '../features/admin/roles'
import { AuthGuard } from '../features/auth/AuthGuard'
import { DashboardPage } from '../pages/DashboardPage'
import { HomePage } from '../pages/HomePage'
import { LoginPage } from '../pages/LoginPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { RegisterPage } from '../pages/RegisterPage'

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route element={<AuthGuard />}>
          <Route path="dashboard" element={<DashboardPage />} />
          {/* RoleGuard is UX only; every /api/v1/admin call is authorized by the backend. */}
          <Route element={<RoleGuard roles={ADMIN_ROLES} />}>
            <Route path="admin" element={<AdminPage />}>
              <Route index element={<AdminOverview />} />
              <Route path="users" element={<UserTable />} />
              <Route path="audit-logs" element={<AuditLogViewer />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
