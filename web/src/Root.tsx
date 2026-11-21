import { useEffect, useState } from 'react'
import App from './App.tsx'
import TestBench from './testbench/TestBench.tsx'

/** /#test shows the hardware test bench; anything else shows the app. */
export default function Root() {
  const [hash, setHash] = useState(location.hash)
  useEffect(() => {
    const onChange = () => setHash(location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return hash === '#test' ? <TestBench /> : <App />
}
