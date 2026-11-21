import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../index.css'
import HapticTestPage from './HapticTestPage'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HapticTestPage />
  </StrictMode>,
)
