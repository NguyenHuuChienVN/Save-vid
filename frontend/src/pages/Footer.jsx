const translations = {
  vi: { rights: "© 2026 SaveVid - Bản quyền thuộc về chúng tôi" },
  en: { rights: "© 2026 SaveVid - All rights reserved" },
};

export default function Footer({ lang = "vi" }) {
  const t = translations[lang];
  return (
    <footer className="border-t text-gray-400 bg-gray-800 border-white/10 mt-6">
      <div className="text-center text-xs sm:text-sm text-gray-400 py-3">
        {t.rights}
      </div>
    </footer>
  );
}