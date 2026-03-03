import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import Connect from "./pages/Connect"
import Dashboard from "./pages/Dashboard"
import History from "./pages/History"
import Navbar from "./components/layout/Navbar"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex flex-col min-h-screen bg-[#FAFAF7]">
          <Navbar />
          <Routes>
            <Route path="/" element={<Navigate to="/connect" replace />} />
            <Route path="/connect" element={<Connect />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}