import { create } from "zustand";

export type Language = "es" | "en";

interface Translations {
  [key: string]: { es: string; en: string };
}

interface LanguageState {
  language: Language;
  setLanguage: (lang: Language) => void;
  toggleLanguage: () => void;
  t: (key: string, params?: Record<string, string>) => string;
}

const translations: Translations = {
  // --- Navigation ---
  "nav.overview": { es: "Resumen", en: "Overview" },
  "nav.inbox": { es: "Inbox", en: "Inbox" },
  "nav.terminal": { es: "Terminal", en: "Terminal" },
  "nav.analysis": { es: "Analisis", en: "Analysis" },
  "nav.screener": { es: "Screener", en: "Screener" },
  "nav.movers": { es: "Movers", en: "Movers" },
  "nav.volatility": { es: "Volatilidad", en: "Volatility" },
  "nav.paper_trade": { es: "Paper Trade", en: "Paper Trade" },
  "nav.rl_trading": { es: "Trading IA", en: "AI Trading" },
  "nav.alerts": { es: "Alertas", en: "Alerts" },
  "nav.chat": { es: "Chat IA", en: "AI Chat" },
  "nav.commodities": { es: "Commodities", en: "Commodities" },
  "nav.macro": { es: "Macro", en: "Macro" },
  "nav.prediction": { es: "Prediccion", en: "Prediction" },
  "nav.recommendations": { es: "Recomendaciones", en: "Recommendations" },
  "nav.connections": { es: "Conexiones", en: "Connections" },
  "nav.calendar": { es: "Calendario", en: "Calendar" },
  "nav.heatmap": { es: "Heatmap", en: "Heatmap" },
  "nav.theses": { es: "Thesis", en: "Theses" },
  "nav.research": { es: "Research", en: "Research" },
  "nav.settings": { es: "Ajustes", en: "Settings" },

  // --- Nav groups ---
  "group.core": { es: "PRINCIPAL", en: "CORE" },
  "group.markets": { es: "MERCADOS", en: "MARKETS" },
  "group.tools": { es: "HERRAMIENTAS", en: "TOOLS" },
  "group.intelligence": { es: "INTELIGENCIA", en: "INTELLIGENCE" },

  // --- Hero Metrics ---
  "hero.portfolio_value": { es: "Valor del Portafolio", en: "Portfolio Value" },
  "hero.daily_pnl": { es: "P&L Diario", en: "Daily P&L" },
  "hero.market_status": { es: "Estado del Mercado", en: "Market Status" },
  "hero.watchlist": { es: "Watchlist", en: "Watchlist" },
  "hero.sentiment": { es: "Sentimiento", en: "Sentiment" },
  "hero.bullish": { es: "Alcista", en: "Bullish" },
  "hero.bearish": { es: "Bajista", en: "Bearish" },
  "hero.neutral": { es: "Neutral", en: "Neutral" },
  "hero.very_bullish": { es: "Muy Alcista", en: "Very Bullish" },
  "hero.very_bearish": { es: "Muy Bajista", en: "Very Bearish" },
  "hero.fear_greed": { es: "Miedo & Codicia", en: "Fear & Greed" },
  "hero.holdings": { es: "{count} posicion(es)", en: "{count} holding(s)" },
  "hero.loading": { es: "Cargando...", en: "Loading..." },
  "hero.open": { es: "Abierto", en: "Open" },
  "hero.closed": { es: "Cerrado", en: "Closed" },
  "hero.us_markets": { es: "Mercados EE.UU. (NYSE/NASDAQ)", en: "US Markets (NYSE/NASDAQ)" },
  "hero.closes_in": { es: "Cierra en {time}", en: "Closes in {time}" },
  "hero.opens_in": { es: "Abre en {time}", en: "Opens in {time}" },
  "hero.tracked_assets": { es: "Activos rastreados", en: "Tracked assets" },
  "hero.et_open": { es: "apertura ET", en: "ET open" },
  "hero.et_close": { es: "cierre ET", en: "ET close" },

  // --- Sections ---
  "section.market_movers": { es: "Movers del Mercado", en: "Market Movers" },
  "section.top_gainers": { es: "Mayores Subidas", en: "Top Gainers" },
  "section.top_losers": { es: "Mayores Bajadas", en: "Top Losers" },
  "section.portfolio_value": { es: "Valor del Portafolio", en: "Portfolio Value" },
  "section.watchlists": { es: "Watchlists", en: "Watchlists" },
  "section.price_chart": { es: "Grafico de Precios", en: "Price Chart" },
  "section.holdings": { es: "Posiciones", en: "Holdings" },

  // --- Actions ---
  "action.load": { es: "Cargar", en: "Load" },
  "action.search": { es: "Buscar", en: "Search" },
  "action.remove": { es: "Quitar", en: "Remove" },

  // --- Status / Messages ---
  "msg.no_holdings": { es: "Sin posiciones. Agrega activos a tu portafolio.", en: "No holdings yet. Add assets to your portfolio." },
  "msg.no_watchlists": { es: "Sin watchlists.", en: "No watchlists yet." },
  "msg.market_unavailable": { es: "Datos de mercado no disponibles", en: "Market data unavailable" },
  "msg.failed_market": { es: "Error al cargar datos de mercado", en: "Failed to load market data" },
  "msg.failed_portfolio": { es: "Error al cargar portafolio", en: "Failed to load portfolio" },
  "msg.enter_symbol": { es: "Ingresa un simbolo para ver historial.", en: "Enter a symbol to view price history." },
  "msg.today": { es: "hoy", en: "today" },
  "msg.shares": { es: "acciones", en: "shares" },
  "msg.assets": { es: "activo(s)", en: "asset(s)" },

  // --- Placeholders ---
  "placeholder.symbol": { es: "Simbolo (ej. AAPL)", en: "Symbol (e.g. AAPL)" },
  "placeholder.new_watchlist": { es: "Nombre de watchlist...", en: "New watchlist name..." },

  // --- View titles ---
  "view.overview.title": { es: "Resumen", en: "Overview" },
  "view.overview.desc": { es: "Resumen del portafolio y mercado", en: "Portfolio summary and market snapshot" },
  "view.inbox.title": { es: "Inbox", en: "Inbox" },
  "view.inbox.desc": { es: "Prioridades del dia con ranking de decision", en: "Decision-ranked daily priorities" },
  "view.terminal.title": { es: "Terminal", en: "Terminal" },
  "view.terminal.desc": { es: "Workspace denso con precio, flujo de noticias, macro y filings", en: "Dense workspace for price, wire, macro and filings" },
  "view.analysis.title": { es: "Analisis", en: "Analysis" },
  "view.analysis.desc": { es: "Analisis tecnico, sentimiento y senales", en: "Technical analysis, sentiment, and signals" },
  "view.screener.title": { es: "Screener", en: "Screener" },
  "view.screener.desc": { es: "Escaneo de mercados con filtros personalizados", en: "Scan markets with custom filters" },
  "view.movers.title": { es: "Market Movers", en: "Market Movers" },
  "view.movers.desc": { es: "Mayores subidas y bajadas del mercado", en: "Top gainers and losers across markets" },
  "view.volatility.title": { es: "Volatilidad", en: "Volatility" },
  "view.volatility.desc": { es: "Metricas de volatilidad y rangos", en: "Volatility metrics and range analysis" },
  "view.paper-trade.title": { es: "Paper Trading", en: "Paper Trading" },
  "view.paper-trade.desc": { es: "Practica estrategias con capital virtual", en: "Practice strategies with virtual capital" },
  "view.rl-trading.title": { es: "Agente RL", en: "RL Trading Agent" },
  "view.rl-trading.desc": { es: "Trading automatizado con aprendizaje por refuerzo", en: "Automated trading with reinforcement learning" },
  "view.alerts.title": { es: "Alertas", en: "Alerts" },
  "view.alerts.desc": { es: "Alertas de precio e historial de notificaciones", en: "Price alerts and notification history" },
  "view.chat.title": { es: "Chat IA", en: "AI Chat" },
  "view.chat.desc": { es: "Pregunta a MyInvestIA sobre mercados y estrategias", en: "Ask MyInvestIA about markets and strategies" },
  "view.commodities.title": { es: "Commodities", en: "Commodities" },
  "view.commodities.desc": { es: "Materias primas: metales, energia y agricultura", en: "Raw materials: metals, energy and agriculture" },
  "view.macro.title": { es: "Macro", en: "Macro Intelligence" },
  "view.macro.desc": { es: "Indicadores economicos globales", en: "Global economic indicators and analysis" },
  "view.prediction.title": { es: "Prediccion IA", en: "AI Prediction" },
  "view.prediction.desc": { es: "Prediccion todo-en-uno sintetizando todas las fuentes de datos", en: "All-in-one prediction synthesizing every data source" },
  "view.recommendations.title": { es: "Recomendaciones IA", en: "AI Recommendations" },
  "view.recommendations.desc": { es: "Recomendaciones diarias basadas en tu portafolio", en: "Daily recommendations based on your portfolio" },
  "view.theses.title": { es: "Thesis", en: "Theses" },
  "view.theses.desc": { es: "Seguimiento de tesis y revisiones", en: "Thesis tracking and review timeline" },
  "view.research.title": { es: "Research", en: "Research" },
  "view.research.desc": { es: "Ranking cuantitativo y snapshots", en: "Quant ranking and snapshots" },
  "view.heatmap.title": { es: "Mapa de Calor Sectorial", en: "Sector Heatmap" },
  "view.heatmap.desc": { es: "Rendimiento por sector con mapa de calor interactivo", en: "Sector performance with interactive heatmap" },
  "view.calendar.title": { es: "Calendario Economico", en: "Economic Calendar" },
  "view.calendar.desc": { es: "Eventos economicos y reportes de ganancias", en: "Economic events and earnings reports" },
  "view.settings.title": { es: "Ajustes", en: "Settings" },
  "view.settings.desc": { es: "Configuracion de la aplicacion y preferencias", en: "Application settings and preferences" },

  // --- Prediction ---
  "prediction.enter_symbol": { es: "Ingresa un simbolo para generar prediccion", en: "Enter a symbol to generate prediction" },
  "prediction.generate": { es: "Predecir", en: "Predict" },
  "prediction.loading": { es: "Analizando todas las fuentes de datos...", en: "Analyzing all data sources..." },
  "prediction.verdict": { es: "Veredicto", en: "Verdict" },
  "prediction.confidence": { es: "Confianza", en: "Confidence" },
  "prediction.technical": { es: "Tecnico", en: "Technical" },
  "prediction.sentiment": { es: "Sentimiento", en: "Sentiment" },
  "prediction.macro": { es: "Macro", en: "Macro" },
  "prediction.news": { es: "Noticias", en: "News" },
  "prediction.social": { es: "Social", en: "Social" },
  "prediction.outlook": { es: "Perspectiva de Precio", en: "Price Outlook" },
  "prediction.short_term": { es: "Corto Plazo (1-2 semanas)", en: "Short Term (1-2 weeks)" },
  "prediction.medium_term": { es: "Mediano Plazo (1-3 meses)", en: "Medium Term (1-3 months)" },
  "prediction.catalysts": { es: "Catalizadores", en: "Catalysts" },
  "prediction.risks": { es: "Riesgos", en: "Risks" },
  "prediction.analysis": { es: "Analisis Completo", en: "Full Analysis" },
  "prediction.strong_buy": { es: "COMPRA FUERTE", en: "STRONG BUY" },
  "prediction.buy": { es: "COMPRAR", en: "BUY" },
  "prediction.neutral": { es: "NEUTRAL", en: "NEUTRAL" },
  "prediction.sell": { es: "VENDER", en: "SELL" },
  "prediction.strong_sell": { es: "VENTA FUERTE", en: "STRONG SELL" },
  "prediction.error": { es: "Error al generar prediccion", en: "Failed to generate prediction" },

  // --- Price Chart ---
  "chart.title": { es: "Gráfico de Precios", en: "Price Chart" },
  "chart.placeholder": { es: "Símbolo (ej. AAPL)", en: "Symbol (e.g. AAPL)" },
  "chart.load": { es: "Cargar", en: "Load" },
  "chart.area": { es: "Área", en: "Area" },
  "chart.candle": { es: "Vela", en: "Candle" },
  "chart.price": { es: "Precio", en: "Price" },
  "chart.empty": { es: "Ingresa un símbolo para ver el historial de precios.", en: "Enter a symbol to view price history." },

  // --- Quote Lookup ---
  "quote.title": { es: "Buscar Cotización", en: "Quote Lookup" },
  "quote.placeholder": { es: "Símbolo (ej. NVDA, BTC)", en: "Symbol (e.g. NVDA, BTC)" },
  "quote.get": { es: "Ver", en: "Get" },
  "quote.prev_close": { es: "Cierre Ant.", en: "Prev Close" },
  "quote.volume": { es: "Volumen", en: "Volume" },
  "quote.market_cap": { es: "Cap. Mercado", en: "Market Cap" },
  "quote.hint": { es: "Busca cotizaciones en tiempo real de acciones, ETFs y crypto.", en: "Look up real-time quotes for stocks, ETFs, and crypto." },
  "quote.quick_picks": { es: "Rápido", en: "Quick" },
  "quote.day_range": { es: "Rango Diario", en: "Day Range" },

  // --- Watchlist ---
  "watchlist.add_placeholder": { es: "Agregar símbolo (ej. AAPL, BTC)", en: "Add symbol (e.g. AAPL, BTC)" },
  "watchlist.empty": { es: "Watchlist vacía. Agrega símbolos arriba.", en: "Empty watchlist. Add symbols above." },
  "action.add": { es: "Agregar", en: "Add" },
  "action.delete_watchlist": { es: "Eliminar watchlist", en: "Delete watchlist" },
  "msg.failed_create": { es: "Error al crear", en: "Failed to create" },
  "msg.failed_delete": { es: "Error al eliminar", en: "Failed to delete" },
  "msg.failed_add": { es: "Error al agregar", en: "Failed to add" },
  "msg.failed_remove": { es: "Error al quitar", en: "Failed to remove" },

  // --- News Feed ---
  "news.title": { es: "Noticias en Tiempo Real", en: "Real-Time News" },
  "news.refresh": { es: "Actualizar", en: "Refresh" },
  "news.impact": { es: "Impacto", en: "Impact" },
  "news.affected_tickers": { es: "Tickers afectados:", en: "Affected tickers:" },
  "news.open_article": { es: "Abrir artículo", en: "Open article" },
  "news.show_less": { es: "Mostrar menos", en: "Show less" },
  "news.show_more": { es: "Ver {count} más", en: "Show {count} more" },
  "news.no_news": { es: "No hay noticias disponibles.", en: "No news available." },
  "news.now": { es: "ahora", en: "now" },
  "news.articles_count": { es: "{count} noticia(s)", en: "{count} article(s)" },
  "news.tab_all": { es: "Todo", en: "All" },
  "news.tab_news": { es: "Noticias", en: "News" },
  "news.tab_social": { es: "Social", en: "Social" },
  "news.tab_blogs": { es: "Blogs", en: "Blogs" },
  "news.upvotes": { es: "votos", en: "upvotes" },
  "news.comments": { es: "comentarios", en: "comments" },

  // --- Connections ---
  "view.connections.title": { es: "Conexiones", en: "Connections" },
  "view.connections.desc": { es: "Conecta exchanges, wallets y brokers para sincronizar posiciones", en: "Connect exchanges, wallets and brokers to sync positions" },
  "conn.add_connection": { es: "Agregar Conexion", en: "Add Connection" },
  "conn.add": { es: "Agregar", en: "Add" },
  "conn.add_first": { es: "Agregar primera conexion", en: "Add first connection" },
  "conn.connect": { es: "Conectar", en: "Connect" },
  "conn.cancel": { es: "Cancelar", en: "Cancel" },
  "conn.sync": { es: "Sincronizar", en: "Sync" },
  "conn.sync_all": { es: "Sincronizar todo", en: "Sync All" },
  "conn.test": { es: "Probar", en: "Test" },
  "conn.holdings": { es: "Posiciones", en: "Holdings" },
  "conn.syncs": { es: "Sincronizaciones", en: "Syncs" },
  "conn.last_sync": { es: "Ultima sinc.", en: "Last sync" },
  "conn.never_synced": { es: "Nunca sincronizado", en: "Never synced" },
  "conn.label": { es: "Nombre", en: "Label" },
  "conn.label_placeholder": { es: "Mi cuenta de Binance...", en: "My Binance account..." },
  "conn.provider": { es: "Proveedor", en: "Provider" },
  "conn.passphrase": { es: "Passphrase (opcional)", en: "Passphrase (optional)" },
  "conn.passphrase_hint": { es: "Solo algunos exchanges (ej. KuCoin)", en: "Some exchanges only (e.g. KuCoin)" },
  "conn.wallet_address": { es: "Direccion de wallet", en: "Wallet address" },
  "conn.optional": { es: "opcional", en: "optional" },
  "conn.etoro_note": { es: "La API de eToro tiene acceso limitado. Tu conexion se guardara y activara cuando el acceso este disponible.", en: "eToro API has limited access. Your connection will be saved and activated when access is available." },
  "conn.sync_success": { es: "{count} posicion(es) sincronizada(s)", en: "{count} holding(s) synced" },
  "conn.sync_failed": { es: "Error al sincronizar", en: "Sync failed" },
  "conn.sync_all_done": { es: "{count}/{total} conexion(es) sincronizada(s)", en: "{count}/{total} connection(s) synced" },
  "conn.delete_confirm": { es: "Eliminar esta conexion y todas sus posiciones sincronizadas?", en: "Delete this connection and all its synced holdings?" },
  "conn.deleted": { es: "Conexion eliminada", en: "Connection deleted" },
  "conn.delete_failed": { es: "Error al eliminar conexion", en: "Failed to delete connection" },
  "conn.test_failed": { es: "Error al probar conexion", en: "Connection test failed" },
  "conn.empty_title": { es: "Sin conexiones", en: "No connections" },
  "conn.empty_desc": { es: "Conecta tu exchange, wallet o broker para sincronizar posiciones automaticamente.", en: "Connect your exchange, wallet or broker to sync positions automatically." },
  "conn.source_exchange": { es: "Exchange", en: "Exchange" },
  "conn.source_wallet": { es: "Wallet", en: "Wallet" },
  "conn.source_broker": { es: "Broker", en: "Broker" },
  "conn.source_prediction": { es: "Prediccion", en: "Prediction" },

  // --- Footer ---
  "footer.disclaimer": {
    es: "MyInvestIA no proporciona asesoramiento financiero. Toda la informacion es solo para apoyo en la toma de decisiones.",
    en: "MyInvestIA does not provide financial advice. All information is for decision support only.",
  },
};

const getInitialLanguage = (): Language => {
  if (typeof window === "undefined") return "es";
  return (localStorage.getItem("oracle-language") as Language) || "es";
};

const useLanguageStore = create<LanguageState>((set, get) => ({
  language: getInitialLanguage(),

  setLanguage: (lang) => {
    localStorage.setItem("oracle-language", lang);
    set({ language: lang });
  },

  toggleLanguage: () => {
    const newLang = get().language === "es" ? "en" : "es";
    localStorage.setItem("oracle-language", newLang);
    set({ language: newLang });
  },

  t: (key, params) => {
    const lang = get().language;
    const entry = translations[key];
    if (!entry) return key;
    let text = entry[lang] || entry.es || key;
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, v);
      });
    }
    return text;
  },
}));

export default useLanguageStore;
