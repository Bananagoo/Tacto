import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '../src/index.css'
import DevTools from './DevTools.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DevTools />
  </StrictMode>,
)
