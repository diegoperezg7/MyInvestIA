"use client";

import {
  createContext,
  useContext,
  useEffect,
  useReducer,
  type ReactNode,
} from "react";

import type { LegacyViewAlias, SectionId, SectionTabId } from "@/types";
import {
  DEFAULT_TAB_BY_SECTION,
  LEGACY_VIEW_TO_SHELL,
  getDefaultTab,
  getStoredShellState,
  isTabForSection,
} from "@/lib/shell";

export type View = LegacyViewAlias;

type FocusView = "asset-detail" | null;

interface ViewContextType {
  activeView: View;
  activeSection: SectionId;
  activeTab: SectionTabId;
  focusView: FocusView;
  setActiveView: (view: View) => void;
  setActiveSection: (section: SectionId, tab?: SectionTabId) => void;
  setActiveTab: (tab: SectionTabId) => void;
  selectedSymbol: string;
  setSelectedSymbol: (symbol: string) => void;
  openAssetDetail: (symbol?: string) => void;
  closeAssetDetail: () => void;
  commandBarOpen: boolean;
  setCommandBarOpen: (open: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: (collapsed: boolean) => void;
  sidebarMobileOpen: boolean;
  setSidebarMobileOpen: (open: boolean) => void;
}

const ViewContext = createContext<ViewContextType | null>(null);

interface ViewState {
  activeSection: SectionId;
  activeTab: SectionTabId;
  activeView: View;
  focusView: FocusView;
  selectedSymbol: string;
  commandBarOpen: boolean;
  sidebarCollapsed: boolean;
  sidebarMobileOpen: boolean;
}

type ViewAction =
  | { type: "setLegacyView"; view: View }
  | { type: "setActiveSection"; section: SectionId; tab?: SectionTabId }
  | { type: "setActiveTab"; tab: SectionTabId }
  | { type: "setSelectedSymbol"; symbol: string }
  | { type: "openAssetDetail"; symbol?: string }
  | { type: "closeAssetDetail" }
  | { type: "setCommandBarOpen"; open: boolean }
  | { type: "setSidebarCollapsed"; collapsed: boolean }
  | { type: "setSidebarMobileOpen"; open: boolean };

function buildLegacyView(
  section: SectionId,
  tab: SectionTabId,
  focusView: FocusView,
): View {
  if (focusView === "asset-detail") {
    return "terminal";
  }

  const match = Object.entries(LEGACY_VIEW_TO_SHELL).find(([, value]) => {
    return value.section === section && value.tab === tab && !value.focus;
  });

  return (match?.[0] as View | undefined) ?? "overview";
}

function sanitizeTab(section: SectionId, tab?: SectionTabId): SectionTabId {
  if (tab && isTabForSection(section, tab)) {
    return tab;
  }
  return getDefaultTab(section);
}

function viewReducer(state: ViewState, action: ViewAction): ViewState {
  switch (action.type) {
    case "setLegacyView": {
      const target = LEGACY_VIEW_TO_SHELL[action.view];
      const section = target.section;
      const tab = sanitizeTab(section, target.tab);
      const focusView = target.focus ?? null;
      return {
        ...state,
        activeSection: section,
        activeTab: tab,
        activeView: action.view,
        focusView,
        sidebarMobileOpen: false,
      };
    }
    case "setActiveSection": {
      const tab = sanitizeTab(action.section, action.tab);
      return {
        ...state,
        activeSection: action.section,
        activeTab: tab,
        activeView: buildLegacyView(action.section, tab, null),
        focusView: null,
        sidebarMobileOpen: false,
      };
    }
    case "setActiveTab": {
      const tab = sanitizeTab(state.activeSection, action.tab);
      return {
        ...state,
        activeTab: tab,
        activeView: buildLegacyView(state.activeSection, tab, null),
        focusView: null,
      };
    }
    case "setSelectedSymbol":
      return { ...state, selectedSymbol: action.symbol };
    case "openAssetDetail":
      return {
        ...state,
        selectedSymbol: action.symbol ?? state.selectedSymbol,
        activeView: "terminal",
        focusView: "asset-detail",
        sidebarMobileOpen: false,
      };
    case "closeAssetDetail":
      return {
        ...state,
        activeView: buildLegacyView(state.activeSection, state.activeTab, null),
        focusView: null,
      };
    case "setCommandBarOpen":
      return { ...state, commandBarOpen: action.open };
    case "setSidebarCollapsed":
      return { ...state, sidebarCollapsed: action.collapsed };
    case "setSidebarMobileOpen":
      return { ...state, sidebarMobileOpen: action.open };
    default:
      return state;
  }
}

function getInitialState(): ViewState {
  const stored = getStoredShellState();
  const activeSection = stored?.section ?? "home";
  const activeTab = sanitizeTab(activeSection, stored?.tab ?? DEFAULT_TAB_BY_SECTION[activeSection]);

  return {
    activeSection,
    activeTab,
    activeView: buildLegacyView(activeSection, activeTab, null),
    focusView: null,
    selectedSymbol: "",
    commandBarOpen: false,
    sidebarCollapsed: false,
    sidebarMobileOpen: false,
  };
}

export function ViewProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(viewReducer, undefined, getInitialState);

  const setActiveView = (view: View) => dispatch({ type: "setLegacyView", view });
  const setActiveSection = (section: SectionId, tab?: SectionTabId) =>
    dispatch({ type: "setActiveSection", section, tab });
  const setActiveTab = (tab: SectionTabId) => dispatch({ type: "setActiveTab", tab });
  const setSelectedSymbol = (symbol: string) =>
    dispatch({ type: "setSelectedSymbol", symbol });
  const openAssetDetail = (symbol?: string) =>
    dispatch({ type: "openAssetDetail", symbol });
  const closeAssetDetail = () => dispatch({ type: "closeAssetDetail" });
  const setCommandBarOpen = (open: boolean) =>
    dispatch({ type: "setCommandBarOpen", open });
  const setSidebarCollapsed = (collapsed: boolean) =>
    dispatch({ type: "setSidebarCollapsed", collapsed });
  const setSidebarMobileOpen = (open: boolean) =>
    dispatch({ type: "setSidebarMobileOpen", open });

  useEffect(() => {
    try {
      localStorage.setItem(
        "myinvestia-shell",
        JSON.stringify({
          section: state.activeSection,
          tab: state.activeTab,
        }),
      );
    } catch {}
  }, [state.activeSection, state.activeTab]);

  return (
    <ViewContext.Provider
      value={{
        activeView: state.activeView,
        activeSection: state.activeSection,
        activeTab: state.activeTab,
        focusView: state.focusView,
        setActiveView,
        setActiveSection,
        setActiveTab,
        selectedSymbol: state.selectedSymbol,
        setSelectedSymbol,
        openAssetDetail,
        closeAssetDetail,
        commandBarOpen: state.commandBarOpen,
        setCommandBarOpen,
        sidebarCollapsed: state.sidebarCollapsed,
        setSidebarCollapsed,
        sidebarMobileOpen: state.sidebarMobileOpen,
        setSidebarMobileOpen,
      }}
    >
      {children}
    </ViewContext.Provider>
  );
}

export function useView() {
  const ctx = useContext(ViewContext);
  if (!ctx) {
    throw new Error("useView must be used within ViewProvider");
  }
  return ctx;
}
