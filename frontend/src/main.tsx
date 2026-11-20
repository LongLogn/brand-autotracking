import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import '@fontsource/be-vietnam-pro/vietnamese-400.css';
import '@fontsource/be-vietnam-pro/vietnamese-500.css';
import '@fontsource/be-vietnam-pro/vietnamese-600.css';
import '@fontsource/be-vietnam-pro/vietnamese-700.css';
import '@fontsource/be-vietnam-pro/latin-400.css';
import '@fontsource/be-vietnam-pro/latin-500.css';
import '@fontsource/be-vietnam-pro/latin-600.css';
import '@fontsource/be-vietnam-pro/latin-700.css';
import './styles.css';
import { App } from './App';
import { ApiApp } from './ApiApp';
import { StoreProvider } from './lib/store';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      {import.meta.env.VITE_DEMO_MODE === 'true' ? <StoreProvider><App /></StoreProvider> : <ApiApp />}
    </BrowserRouter>
  </StrictMode>,
);
