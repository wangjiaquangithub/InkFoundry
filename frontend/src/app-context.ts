import { createContext, useContext } from "react";

export interface BookInfo {
  id: string;
  title: string;
  genre: string;
}

interface AppContextType {
  currentBook: BookInfo | null;
  setCurrentBook: (book: BookInfo | null) => void;
  isRestoringBook: boolean;
}

export const AppContext = createContext<AppContextType>({
  currentBook: null,
  setCurrentBook: () => {},
  isRestoringBook: false,
});

export function useAppContext() {
  return useContext(AppContext);
}

const CURRENT_BOOK_STORAGE_KEY = "inkfoundry.currentBook";

export function loadStoredCurrentBook(): BookInfo | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(CURRENT_BOOK_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<BookInfo>;
    if (
      typeof parsed.id !== "string" ||
      typeof parsed.title !== "string" ||
      typeof parsed.genre !== "string"
    ) {
      return null;
    }

    return {
      id: parsed.id,
      title: parsed.title,
      genre: parsed.genre,
    };
  } catch {
    return null;
  }
}

export function saveCurrentBook(book: BookInfo | null) {
  if (typeof window === "undefined") {
    return;
  }

  if (!book) {
    window.localStorage.removeItem(CURRENT_BOOK_STORAGE_KEY);
    return;
  }

  window.localStorage.setItem(CURRENT_BOOK_STORAGE_KEY, JSON.stringify(book));
}
