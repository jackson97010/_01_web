import { useEffect } from 'react';
import { Play, Pause, SkipBack, SkipForward, ZoomIn, ZoomOut } from 'lucide-react';
import { useStockStore } from '@/stores/stockStore';

export default function TimelineControls() {
  const {
    stockData,
    isPlaying,
    playbackSpeed,
    currentTimeIndex,
    zoomMode,
    togglePlayback,
    setPlaybackSpeed,
    setCurrentTimeIndex,
    toggleZoomMode,
  } = useStockStore();

  // 自動播放邏輯
  useEffect(() => {
    if (!isPlaying || !stockData?.unifiedTimeline) return;

    const maxIndex = stockData.unifiedTimeline.length - 1;
    if (currentTimeIndex >= maxIndex) {
      togglePlayback(); // 播放到底自動停止
      return;
    }

    const interval = setInterval(() => {
      setCurrentTimeIndex(Math.min(currentTimeIndex + 1, maxIndex));
    }, 1000 / playbackSpeed);

    return () => clearInterval(interval);
  }, [isPlaying, currentTimeIndex, playbackSpeed, stockData, setCurrentTimeIndex, togglePlayback]);

  if (!stockData?.unifiedTimeline || stockData.unifiedTimeline.length === 0) {
    return null;
  }

  const maxIndex = stockData.unifiedTimeline.length - 1;
  const currentTime = stockData.unifiedTimeline[currentTimeIndex];

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentTimeIndex(parseInt(e.target.value, 10));
  };

  const handleSkipBack = () => {
    setCurrentTimeIndex(Math.max(0, currentTimeIndex - 10));
  };

  const handleSkipForward = () => {
    setCurrentTimeIndex(Math.min(maxIndex, currentTimeIndex + 10));
  };

  return (
    <div className="bg-black border border-gray-800 rounded p-3">
      <div className="flex items-center gap-3">
        {/* 播放控制按鈕 */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleSkipBack}
            className="p-2 rounded bg-gray-900 hover:bg-gray-800 text-gray-400 hover:text-yellow-400 transition-colors"
            title="後退 10 秒"
          >
            <SkipBack className="w-4 h-4" />
          </button>

          <button
            onClick={togglePlayback}
            className="p-2 rounded-full bg-yellow-400 hover:bg-yellow-500 text-black transition-colors"
            title={isPlaying ? '暫停' : '播放'}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>

          <button
            onClick={handleSkipForward}
            className="p-2 rounded bg-gray-900 hover:bg-gray-800 text-gray-400 hover:text-yellow-400 transition-colors"
            title="前進 10 秒"
          >
            <SkipForward className="w-4 h-4" />
          </button>
        </div>

        {/* 時間軸滑桿 */}
        <div className="flex-1 flex items-center gap-3">
          <input
            type="range"
            min="0"
            max={maxIndex}
            value={currentTimeIndex}
            onChange={handleSliderChange}
            className="flex-1 h-1.5 bg-gray-800 rounded-lg appearance-none cursor-pointer accent-yellow-400"
          />
          <span className="text-xs font-mono text-yellow-400 min-w-[100px]">
            {currentTime}
          </span>
        </div>

        {/* 縮放模式 */}
        <button
          onClick={toggleZoomMode}
          className="p-2 rounded bg-gray-900 hover:bg-gray-800 text-gray-400 hover:text-yellow-400 transition-colors"
          title={zoomMode === 'dynamic' ? '切換到完整時間軸' : '切換到動態縮放'}
        >
          {zoomMode === 'dynamic' ? (
            <ZoomOut className="w-4 h-4" />
          ) : (
            <ZoomIn className="w-4 h-4" />
          )}
        </button>

        {/* 播放速度 */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 font-mono">速度:</span>
          <select
            value={playbackSpeed}
            onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}
            className="px-2 py-1 text-xs border border-gray-700 rounded bg-black text-white font-mono"
          >
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="2">2x</option>
            <option value="5">5x</option>
            <option value="10">10x</option>
            <option value="20">20x</option>
            <option value="30">30x</option>
            <option value="50">50x</option>
          </select>
        </div>
      </div>

      {/* 進度指示 */}
      <div className="mt-2 flex justify-between text-xs text-gray-500 font-mono">
        <span>
          {currentTimeIndex + 1} / {maxIndex + 1} 筆
        </span>
        <span>
          {((currentTimeIndex / maxIndex) * 100).toFixed(1)}%
        </span>
      </div>
    </div>
  );
}
