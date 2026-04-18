import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  AppContext,
  loadStoredCurrentBook,
  normalizeBookInfo,
  saveCurrentBook,
  useAppContext,
  type BookInfo,
} from "./app-context";
import { api } from "./api/client";
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

  const setCurrentBook = useCallback((book: BookInfo | null) => {
    setCurrentBookState(book);
    saveCurrentBook(book);
    if (book) {
      setRestoreIssue(null);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const restoreProjectContext = async () => {
      const storedBook = loadStoredCurrentBook();
      try {
        const res = await api.getActiveProject();
        const project = res.data.project ? normalizeBookInfo(res.data.project) : null;
        if (!cancelled) {
          setCurrentBook(project);
          if (!project && storedBook) {
            setRestoreIssue("上次选中的项目已失效或被删除，请重新选择一个项目。");
          }
        }
      } catch {
        if (!cancelled) {
          setCurrentBook(null);
          if (storedBook) {
            setRestoreIssue("项目上下文恢复失败，请重新确认项目后继续。");
          }
        }
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
  }, [setCurrentBook]);

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
