import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import axios from "axios";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import {
  AppContext,
  loadStoredCurrentBook,
  normalizeBookInfo,
  saveCurrentBook,
  useAppContext,
  type BookInfo,
} from "./app-context";
import { api, type ProjectRecord } from "./api/client";
import { Projects } from "./pages/Projects";
import { Outline } from "./pages/Outline";
import { Chapters } from "./pages/Chapters";
import { Characters } from "./pages/Characters";
import { WorldBuilder } from "./pages/WorldBuilder";
import { Settings } from "./pages/Settings";
import { Tokens } from "./pages/Tokens";
import { StyleAnalysis } from "./pages/StyleAnalysis";
import { AIDetection } from "./pages/AIDetection";
import { TrendIntelligence } from "./pages/TrendIntelligence";

interface NavItem {
  path: string;
  label: string;
  icon: string;
  bookRequired?: boolean;
}

function Sidebar() {
  const location = useLocation();
  const { currentBook } = useAppContext();

  const bookNavItems: NavItem[] = [
    { path: "/outline", label: "大纲", icon: "📋", bookRequired: true },
    { path: "/chapters", label: "章节", icon: "📚", bookRequired: true },
    { path: "/characters", label: "角色", icon: "👥", bookRequired: true },
    { path: "/world", label: "世界观", icon: "🌍", bookRequired: true },
    { path: "/style", label: "风格分析", icon: "🎨", bookRequired: true },
    { path: "/ai-detect", label: "AI检测", icon: "🔍", bookRequired: true },
    { path: "/tokens", label: "Token 用量", icon: "📊", bookRequired: true },
    { path: "/settings", label: "设置", icon: "⚙️", bookRequired: true },
  ];

  const systemNavItems: NavItem[] = [
    { path: "/", label: "书籍管理", icon: "📖" },
    { path: "/trends", label: "趋势洞察", icon: "📈" },
  ];

  const navClass = (path: string) => {
    const isActive = location.pathname === path;
    const item = [...bookNavItems, ...systemNavItems].find((i) => i.path === path);
    if (isActive) return "bg-blue-50 text-blue-700 font-medium";
    if (item?.bookRequired && !currentBook) return "text-gray-300 cursor-not-allowed";
    return "text-gray-600 hover:bg-gray-100";
  };

  const handleNav = (path: string) => (e: React.MouseEvent) => {
    const item = [...bookNavItems, ...systemNavItems].find((i) => i.path === path);
    if (item?.bookRequired && !currentBook) {
      e.preventDefault();
    }
  };

  return (
    <aside className="w-52 bg-white border-r flex flex-col">
      {/* App title */}
      <div className="px-4 py-4 border-b">
        <h1 className="text-lg font-bold text-gray-800">InkFoundry</h1>
      </div>

      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {/* System menu */}
        {systemNavItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition ${navClass(item.path)}`}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}

        {/* Divider + Book menu - only shown when a book is selected */}
        {currentBook && (
          <>
            <div className="border-t my-2" />
            <div className="px-3 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              {currentBook.title}
            </div>
            {bookNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition ${navClass(item.path)}`}
                onClick={handleNav(item.path)}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
          </>
        )}
      </nav>
    </aside>
  );
}

function AppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}

// Guard: redirects to home if no book is selected
function BookGuard({ children }: { children: ReactNode }) {
  const { currentBook, isRestoringBook } = useAppContext();

  if (isRestoringBook) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-400">正在恢复项目上下文...</p>
      </div>
    );
  }

  if (!currentBook) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function App() {
  const [currentBook, setCurrentBookState] = useState<BookInfo | null>(() => loadStoredCurrentBook());
  const [isRestoringBook, setIsRestoringBook] = useState(true);
  const [restoreIssue, setRestoreIssue] = useState<string | null>(null);
  const syncRequestIdRef = useRef(0);
  const currentBookRef = useRef<BookInfo | null>(currentBook);
  const lastReconcileAtRef = useRef(0);

  const booksEqual = useCallback((left: BookInfo | null, right: BookInfo | null) => {
    if (left === right) {
      return true;
    }
    if (!left || !right) {
      return false;
    }
    return left.id === right.id
      && left.title === right.title
      && left.genre === right.genre
      && left.summary === right.summary
      && left.targetChapters === right.targetChapters;
  }, []);

  const setCurrentBook = useCallback((book: BookInfo | null) => {
    syncRequestIdRef.current += 1;
    currentBookRef.current = book;
    setCurrentBookState((prev) => (booksEqual(prev, book) ? prev : book));
    saveCurrentBook(book);
    if (book) {
      setRestoreIssue(null);
    }
  }, [booksEqual]);

  const normalizeActiveProject = useCallback((project: ProjectRecord | null): BookInfo | null => {
    return project ? normalizeBookInfo(project) : null;
  }, []);

  const syncProjectContext = useCallback(async (options?: { preserveCurrentBookOnFailure?: boolean }) => {
    const storedBook = loadStoredCurrentBook();
    const preserveCurrentBookOnFailure = options?.preserveCurrentBookOnFailure ?? false;
    const requestId = ++syncRequestIdRef.current;

    try {
      const res = await api.getActiveProject();
      if (requestId !== syncRequestIdRef.current) {
        return null;
      }
      const project = normalizeActiveProject(res.data.project);
      setCurrentBook(project);
      if (!project && storedBook) {
        setRestoreIssue("上次选中的项目已失效或被删除，请重新选择一个项目。");
      }
      return project;
    } catch (error: unknown) {
      if (requestId !== syncRequestIdRef.current) {
        return null;
      }
      if (axios.isAxiosError(error) && error.response?.status === 409) {
        setCurrentBook(null);
        setRestoreIssue("当前项目上下文已失效，请重新选择一个项目。");
        return null;
      }

      if (!preserveCurrentBookOnFailure) {
        setCurrentBook(null);
      }
      if (storedBook) {
        setRestoreIssue("项目上下文恢复失败，请重新确认项目后继续。");
      }
      return preserveCurrentBookOnFailure ? currentBookRef.current : null;
    }
  }, [normalizeActiveProject, setCurrentBook]);

  useEffect(() => {
    let cancelled = false;

    const restoreProjectContext = async () => {
      try {
        await syncProjectContext();
      } finally {
        if (!cancelled) {
          setIsRestoringBook(false);
        }
      }
    };

    void restoreProjectContext();

    return () => {
      cancelled = true;
    };
  }, [syncProjectContext]);

  useEffect(() => {
    if (isRestoringBook || typeof window === "undefined") {
      return;
    }

    let cancelled = false;

    const reconcile = async () => {
      const now = Date.now();
      if (now - lastReconcileAtRef.current < 300) {
        return;
      }
      lastReconcileAtRef.current = now;
      await syncProjectContext({ preserveCurrentBookOnFailure: true });
      if (cancelled) {
        return;
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void reconcile();
      }
    };

    const handleFocus = () => {
      void reconcile();
    };

    window.addEventListener("focus", handleFocus);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      cancelled = true;
      window.removeEventListener("focus", handleFocus);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isRestoringBook, syncProjectContext]);

  return (
    <AppContext.Provider
      value={{
        currentBook,
        setCurrentBook,
        isRestoringBook,
        restoreIssue,
        clearRestoreIssue: () => setRestoreIssue(null),
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={
              <AppLayout>
                <Projects />
              </AppLayout>
            }
          />
          <Route
            path="/tokens"
            element={
              <AppLayout>
                <BookGuard>
                  <Tokens />
                </BookGuard>
              </AppLayout>
            }
          />
          <Route
            path="/outline"
            element={
              <AppLayout>
                <BookGuard>
                  <Outline />
                </BookGuard>
              </AppLayout>
            }
          />
          <Route
            path="/chapters"
            element={
              <AppLayout>
                <BookGuard>
                  <Chapters />
                </BookGuard>
              </AppLayout>
            }
          />
          <Route
            path="/characters"
            element={
              <AppLayout>
                <BookGuard>
                  <Characters />
                </BookGuard>
              </AppLayout>
            }
          />
          <Route
            path="/world"
            element={
              <AppLayout>
                <BookGuard>
                  <WorldBuilder />
                </BookGuard>
              </AppLayout>
            }
          />
          <Route
            path="/settings"
            element={
              <AppLayout>
                <BookGuard>
                  <Settings />
                </BookGuard>
              </AppLayout>
            }
          />
          <Route
            path="/trends"
            element={
              <AppLayout>
                <TrendIntelligence />
              </AppLayout>
            }
          />
          <Route
            path="/style"
            element={
              <AppLayout>
                <BookGuard>
                  <StyleAnalysis />
                </BookGuard>
              </AppLayout>
            }
          />
          <Route
            path="/ai-detect"
            element={
              <AppLayout>
                <BookGuard>
                  <AIDetection />
                </BookGuard>
              </AppLayout>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AppContext.Provider>
  );
}

export default App;
