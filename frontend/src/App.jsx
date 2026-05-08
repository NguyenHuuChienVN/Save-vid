import { useState } from "react";
import Header from "./pages/Header";
import Footer from "./pages/Footer";
import Download from "./components/Download";

function App() {
  const [lang, setLang] = useState("vi");
  return (
    <div className="min-h-screen text-black flex flex-col">
      <Header lang={lang} setLang={setLang} />

      <div className="flex-1 flex items-center justify-center">
        <Download lang={lang} />
      </div>
        <Footer lang={lang} />
    </div>
  );
}

export default App;