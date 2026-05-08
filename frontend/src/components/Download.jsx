import { useState, useEffect } from "react"
import axios from "axios";
import { LuArrowDownToLine } from "react-icons/lu";

const translations = {
  vi: {
    title: "SaveVid - Tải Video TikTok, YouTube Không Logo, Miễn Phí",
    subtitle: "Tải video TikTok không logo, watermark. Hỗ trợ YouTube, Douyin HD, 4K miễn phí trên điện thoại và máy tính.",
    placeholder: "Dán link TikTok / YouTube tại đây...",
    downloading: "Đang tải...",
    download: "Tải Xuống",
    copyLink: "Sao chép link",
    copied: "Đã copy!",
    pleaseEnterUrl: "Vui lòng nhập link!",
    history: "Lịch sử tải:",
    noHistory: "Chưa có lịch sử",
    reuse: "Dùng lại",
    successDownload: "✅ Tải xuống thành công!",
    playlist: (n) => `✅ Playlist: ${n} file`,
    invalidData: "⚠️ Dữ liệu trả về không hợp lệ.",
    errorDownload: "❌ Lỗi tải xuống! Kiểm tra lại link.",
  },
  en: {
    title: "SaveVid - Download TikTok, YouTube Videos Free, No Watermark",
    subtitle: "Download TikTok videos without watermark. Supports YouTube, Douyin HD, 4K for free on mobile and desktop.",
    placeholder: "Paste TikTok / YouTube link here...",
    downloading: "Downloading...",
    download: "Download",
    copyLink: "Copy Link",
    copied: "Copied!",
    pleaseEnterUrl: "Please enter a link!",
    history: "Download history:",
    noHistory: "No history yet",
    reuse: "Use again",
    successDownload: "✅ Download successful!",
    playlist: (n) => `✅ Playlist: ${n} files`,
    invalidData: "⚠️ Invalid response data.",
    errorDownload: "❌ Download error! Please check the link.",
  },
};

function Download({ lang = "vi" }) {
    const [url, setUrl] = useState("");
    const [loading, setLoading] = useState(false);
    const [quality, setQuality] = useState("1080");
    const [progress, setProgress] = useState(0);
    const [history, setHistory] = useState([]);
    const [message, setMessage] = useState(null);
    const [preview, setPreview] = useState(null);

    const t = translations[lang];
    const API = "https://kindle-landslide-revenue.ngrok-free.dev/";

    useEffect(() => {
        setHistory(JSON.parse(localStorage.getItem("history")) || []);
    }, []);

    const saveHistory = (link) => {
        const newData = [link, ...history.filter((h) => h !== link)].slice(0, 5);
        setHistory(newData);
        localStorage.setItem("history", JSON.stringify(newData));
    };

const handleDownload = async () => {
    if (!url) return alert("Nhập link");

    setLoading(true);
    setMessage(null);

    try {
        const res = await axios.get(`${API}/download`, {
            params: { url, quality },
            headers: { "ngrok-skip-browser-warning": "true" },
            responseType: "blob",
        });
        

        const data = res.data;

        // 🎬 preview
        setPreview({
            title: data.title,
            thumbnail: data.thumbnail,
            duration: data.duration,
            url: data.url
        });

        // 👉 mở download

        setMessage("Tải thành công");
        saveHistory(url);

    } catch (err) {
        console.error(err);
        setMessage("Lỗi tải video");
    } finally {
        setLoading(false);
    }
};


    return (
        <div className="w-full max-w-2xl px-4 mx-auto text-center">
            {/* Tiêu đề */}
            <h1 className="text-xl sm:text-2xl font-bold text-black mb-3">{t.title}</h1>
            <p className="text-sm text-gray-500 mb-6">{t.subtitle}</p>

            {/* Input + nút cùng hàng */}
            <div className="flex flex-col sm:flex-row items-center bg-white rounded-lg overflow-hidden shadow-lg">
                <span className="pl-4 hidden sm:block text-gray-400 text-lg">🔗</span>
                <input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleDownload()}
                    placeholder={t.placeholder}
                    className="flex-1 px-3 py-3 text-base outline-none text-gray-700"
                    type="text"
                />
                <div className="flex w-full sm:w-auto">
                    <select
                        value={quality}
                        onChange={(e) => setQuality(e.target.value)}
                        className="px-2 py-3 text-sm border-l border-gray-200 outline-none text-gray-600 bg-white"
                    >
                        <option value="1080">1080p</option>
                        <option value="720">720p</option>
                        <option value="480">480p</option>
                        <option value="360">360p</option>
                    </select>
                    <button
                        onClick={handleDownload}
                        className=" w-full sm:w-auto bg-yellow-200 hover:bg-yellow-300 text-gray-700 px-5 py-3 font-bold text-sm sm:text-base disabled:opacity-50 transition-colors rouded-r-lg"
                        disabled={loading}
                    >
                        {loading ?  `${t.downloading} ${progress}%` : 
                        <><LuArrowDownToLine size={15} className="inline mr-1" /> {t.download}</>}
                    </button>
                </div>
            </div>

            {/* Progress bar */}
            {loading && (
            <>
                <p>Đang tải...</p>

                    <div className="mt-4">
                        <div className="h-2 bg-white/30 rounded overflow-hidden">
                            <div
                            className="h-2 bg-white rounded transition-all duration-300"
                            style={{ width: `${progress}%` }}
                            />
                        </div>
                            <p className="text-xs text-white/70 mt-1">{progress}%</p>
                   </div>
            </>
            )}

            {/* Thông báo */}
            {message && (
                <p className="mt-3 text-sm text-black">{message}</p>
            )}

            {/* Lịch sử */}
            <div className="mt-6 text-left">
                <h3 className="font-bold mb-2 text-sm text-black">{t.history}</h3>
                {history.length === 0 && (
                    <p className="text-xs text-black/50">{t.noHistory}</p>
                )}
                {history.map((h, i) => (
                    <div
                        key={i}
                        className="flex items-center justify-between bg-black/10 px-3 py-2 rounded mb-2 text-xs sm:text-sm"
                    >
                        <span className="truncate max-w-xs text-black">{h}</span>
                        <button
                            onClick={() => setUrl(h)}
                            className="text-green-500 hover:underline ml-2 shrink-0"
                        >
                            {t.reuse}
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
    };
export default Download;