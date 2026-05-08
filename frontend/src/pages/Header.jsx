export default function Header({ lang, setLang }) {
  return (
    <header className="bg-white backdrop-blur border-b shadow-xl border-white/10">
      <div className="max-w-6xl mx-auto px-4 py-3 flex justify-between items-center">
        <img className="cursor-pointer" src="/savevid-logo.svg" alt="logo" onClick={() => window.location.reload()} />

        <div className="flex items-center border border-gray-200 rounded-full overflow-hidden text-xs font-medium">
          <button
            onClick={() => setLang("vi")}
            className={`px-3 py-1 transition-colors ${
              lang === "vi" ? "bg-gray-900 text-white" : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            VI
          </button>
          <button
            onClick={() => setLang("en")}
            className={`px-3 py-1 transition-colors ${
              lang === "en" ? "bg-gray-900 text-white" : "text-gray-500 hover:bg-gray-100"
            }`}
          >
            EN
          </button>
        </div>
      </div>
    </header>
  );
}