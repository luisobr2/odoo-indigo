import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App.jsx'
import './styles.css'

// HashRouter: las rutas van despues del # para no chocar con wp-admin.php?page=indigo
ReactDOM.createRoot(document.getElementById('indigo-root')).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
)
