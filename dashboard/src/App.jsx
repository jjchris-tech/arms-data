import { useEffect } from 'react'
import { Link, Route, Routes, useLocation } from 'react-router-dom'
import CountryList from './components/CountryList'
import CountryPage from './components/CountryPage'
import DataPage from './components/DataPage'
import Method from './components/Method'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <ScrollToTop />
      <header className="border-b border-stone-200 dark:border-stone-800">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="font-semibold tracking-tight">Arms Dependency</Link>
          <nav className="flex gap-5 text-sm text-stone-600 dark:text-stone-400">
            <Link to="/" className="hover:text-stone-900 dark:hover:text-stone-100">Countries</Link>
            <Link to="/method" className="hover:text-stone-900 dark:hover:text-stone-100">Method</Link>
            <Link to="/data" className="hover:text-stone-900 dark:hover:text-stone-100">Data</Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 w-full max-w-5xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<CountryList />} />
          <Route path="/country/:iso3" element={<CountryPage />} />
          <Route path="/method" element={<Method />} />
          <Route path="/data" element={<DataPage />} />
          <Route path="*" element={<p>Page not found. <Link className="underline" to="/">Back to countries</Link></p>} />
        </Routes>
      </main>

      <footer className="border-t border-stone-200 dark:border-stone-800 text-xs text-stone-500">
        <div className="max-w-5xl mx-auto px-4 py-5">
          Information from the Stockholm International Peace Research Institute (SIPRI),{' '}
          <a className="underline" href="https://www.sipri.org/databases/armstransfers" target="_blank" rel="noreferrer">sipri.org/databases/armstransfers</a>.
          Estimates and analysis are this site’s own, not SIPRI’s. Imported equipment only — domestic production is not
          covered. <Link to="/method" className="underline">How this works</Link>.
        </div>
      </footer>
    </div>
  )
}
