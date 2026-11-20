// State tạm trong bộ nhớ trình duyệt, thay cho API (Lambda/FastAPI) khi backend chưa có.
// Khi nối API, thay các hàm trong context này bằng lời gọi HTTP có JWT của Cognito.

import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  INITIAL_ALERTS,
  INITIAL_ANALYSES,
  INITIAL_BRANDS,
  INITIAL_RULES,
  INITIAL_RUNS,
  POSTS_FIXTURE,
} from '../data/mock';
import type { Alert, AlertRule, AnalysisResult, Brand, Post, Run } from '../data/types';

interface Toast {
  id: number;
  text: string;
  tone: 'ok' | 'error';
}

interface Store {
  signedIn: boolean;
  signIn: () => void;
  signOut: () => void;
  brands: Brand[];
  runs: Run[];
  posts: Post[];
  rules: AlertRule[];
  alerts: Alert[];
  analyses: AnalysisResult[];
  saveBrand: (brand: Brand) => void;
  deleteBrand: (id: string) => void;
  setActive: (id: string, active: boolean) => void;
  saveRule: (rule: AlertRule) => void;
  markAlertsRead: (brandId: string) => void;
  addAnalysis: (a: AnalysisResult) => void;
  toast: Toast | null;
  notify: (text: string, tone?: Toast['tone']) => void;
}

const Ctx = createContext<Store | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [signedIn, setSignedIn] = useState(true);
  const [brands, setBrands] = useState(INITIAL_BRANDS);
  const [rules, setRules] = useState(INITIAL_RULES);
  const [alerts, setAlerts] = useState(INITIAL_ALERTS);
  const [analyses, setAnalyses] = useState(INITIAL_ANALYSES);
  const [toast, setToast] = useState<Toast | null>(null);
  const timer = useRef<number>();

  const notify = useCallback((text: string, tone: Toast['tone'] = 'ok') => {
    window.clearTimeout(timer.current);
    setToast({ id: Date.now(), text, tone });
    timer.current = window.setTimeout(() => setToast(null), 4000);
  }, []);

  const value = useMemo<Store>(
    () => ({
      signedIn,
      signIn: () => setSignedIn(true),
      signOut: () => setSignedIn(false),
      brands,
      runs: INITIAL_RUNS,
      posts: POSTS_FIXTURE,
      rules,
      alerts,
      analyses,
      saveBrand: (brand) =>
        setBrands((list) => (list.some((b) => b.id === brand.id) ? list.map((b) => (b.id === brand.id ? brand : b)) : [...list, brand])),
      deleteBrand: (id) => setBrands((list) => list.filter((b) => b.id !== id)),
      setActive: (id, active) => setBrands((list) => list.map((b) => (b.id === id ? { ...b, active } : b))),
      saveRule: (rule) =>
        setRules((list) => (list.some((r) => r.id === rule.id) ? list.map((r) => (r.id === rule.id ? rule : r)) : [...list, rule])),
      markAlertsRead: (brandId) => setAlerts((list) => list.map((a) => (a.brandId === brandId ? { ...a, read: true } : a))),
      addAnalysis: (a) => setAnalyses((list) => [a, ...list]),
      toast,
      notify,
    }),
    [signedIn, brands, rules, alerts, analyses, toast, notify],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useStore() {
  const s = useContext(Ctx);
  if (!s) throw new Error('useStore phải dùng trong StoreProvider');
  return s;
}

export function useBrandData(brandId: string) {
  const s = useStore();
  return useMemo(
    () => ({
      brand: s.brands.find((b) => b.id === brandId),
      runs: s.runs.filter((r) => r.brandId === brandId).sort((a, b) => a.startedAt.localeCompare(b.startedAt)),
      posts: s.posts.filter((p) => p.brandId === brandId),
      rules: s.rules.filter((r) => r.brandId === brandId),
      alerts: s.alerts.filter((a) => a.brandId === brandId),
      analyses: s.analyses.filter((a) => a.brandId === brandId),
    }),
    [s.brands, s.runs, s.posts, s.rules, s.alerts, s.analyses, brandId],
  );
}
