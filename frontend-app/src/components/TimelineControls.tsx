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
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
      <div className="flex items-center gap-4">
        {/* 播放控制按鈕 */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleSkipBack}
            className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="後退 10 秒"
          >
            <SkipBack className="w-5 h-5" />
          </button>

          <button
            onClick={togglePlayback}
            className="p-3 rounded-full bg-blue-600 hover:bg-blue-700 text-white transition-colors"
            title={isPlaying ? '暫停' : '播放'}
          >
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
          </button>

          <button
            onClick={handleSkipForward}
            className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="前進 10 秒"
          >
            <SkipForward className="w-5 h-5" />
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
            className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
          />
          <span className="text-sm font-mono text-gray-600 dark:text-gray-400 min-w-[120px]">
            {currentTime}
          </span>
        </div>

        {/* 縮放模式 */}
        <button
          onClick={toggleZoomMode}
          className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          title={zoomMode === 'dynamic' ? '切換到完整時間軸' : '切換到動態縮放'}
        >
          {zoomMode === 'dynamic' ? (
            <ZoomOut className="w-5 h-5" />
          ) : (
            <ZoomIn className="w-5 h-5" />
          )}
        </button>

        {/* 播放速度 */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">速度:</span>
          <select
            value={playbackSpeed}
            onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value))}
            className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="2">2x</option>
            <option value="5">5x</option>
            <option value="10">10x</option>
          </select>
        </div>
      </div>

      {/* 進度指示 */}
      <div className="mt-2 flex justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>
          {currentTimeIndex + 1} / {maxIndex + 1} 筆資料
        </span>
        <span>
          {((currentTimeIndex / maxIndex) * 100).toFixed(1)}% 完成
        </span>
      </div>
    </div>
  );
}
