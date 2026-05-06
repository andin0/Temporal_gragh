<template>
  <div class="app">
    <!-- Toast Notification -->
    <div v-if="toastMessage" class="toast-container" :class="{ show: toastVisible }">
      <div class="toast">
        <div class="toast-icon">⚠️</div>
        <div class="toast-text">{{ toastMessage }}</div>
        <button class="toast-close" @click="hideToast">✕</button>
      </div>
    </div>

    <!-- Global Loading Mask -->
    <div v-if="isLoading" class="loading-mask">
      <div class="loading-content">
        <div class="loading-spinner"></div>
        <div class="loading-text">正在进行图计算与智能分析...</div>
      </div>
    </div>

    <header class="control-bar">
      <h1>时序图可视化</h1>
      <div class="buttons">
        <div class="upload-btn-container">
          <button class="cyber-btn" @click="triggerFileUpload">上传数据 (CSV/JSON)</button>
          <input 
            type="file" 
            ref="fileInput" 
            style="display: none" 
            accept=".csv,.json"
            @change="handleFileUpload"
          />
        </div>
      </div>
    </header>
    <main class="graph-container">
      <!-- Enhanced Empty State -->
      <div v-if="!graphData && !isLoading" class="empty-state">
        <div class="empty-icon">📊</div>
        <div class="empty-title">暂无数据</div>
        <div class="empty-description">请点击上方按钮上传 CSV/JSON 文件进行图分析</div>
      </div>
      <GraphView v-if="graphData && !isLoading" :graphData="graphData" :mode="currentMode" />
    </main>
    <!-- 快照模式的时间轴 -->
    <footer class="timeline" v-if="currentMode === 'snapshot' && snapshots.length > 0">
      <div class="timeline-controls">
        <button @click="togglePlayPause" class="cyber-btn play-pause-btn">
          {{ isPlaying ? '⏸ 暂停' : '▶ 播放' }}
        </button>
        <div class="speed-control">
          <label class="speed-label">速度:</label>
          <select v-model="playbackSpeed" class="speed-select">
            <option value="0.5">0.5x</option>
            <option value="1">1x</option>
            <option value="2">2x</option>
          </select>
        </div>
        <input 
          type="range" 
          class="timeline-slider" 
          :min="0" 
          :max="snapshots.length - 1" 
          v-model.number="currentIndex"
          @input="handleSliderInput"
        />
        <div class="current-time">
          时间: {{ currentSnapshot?.timestamp || 0 }}
        </div>
      </div>
    </footer>
    <!-- 时间戳模式的时间窗口过滤器 -->
    <footer class="timeline" v-else-if="currentMode === 'timestamp' && fullTimestampData">
      <div class="timeline-controls">
        <div class="time-window-container">
          <div class="time-label">起始时间: {{ selectedTimeWindow[0] }}</div>
          <input 
            type="range" 
            class="timeline-slider" 
            :min="timeRange[0]" 
            :max="timeRange[1]" 
            :step="1"
            v-model.number="selectedTimeWindow[0]"
            @input="updateTimeWindow"
          />
        </div>
        <div class="time-window-container">
          <div class="time-label">结束时间: {{ selectedTimeWindow[1] }}</div>
          <input 
            type="range" 
            class="timeline-slider" 
            :min="timeRange[0]" 
            :max="timeRange[1]" 
            :step="1"
            v-model.number="selectedTimeWindow[1]"
            @input="updateTimeWindow"
          />
        </div>
        <div class="current-time">
          时间窗口: [{{ selectedTimeWindow[0] }}, {{ selectedTimeWindow[1] }}]
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import GraphView from './components/GraphView.vue'
import { fetchTimestampGraph, fetchSnapshotGraphs, uploadGraphFile } from './api.js'

const graphData = ref(null)
const snapshots = ref([])
const currentIndex = ref(0)
const isPlaying = ref(false)
const playbackSpeed = ref(1)
const isLoading = ref(false)
const toastMessage = ref('')
const toastVisible = ref(false)
let toastTimeout = null
let playInterval = null

// 文件输入框引用
const fileInput = ref(null)

// 新增状态管理
const currentMode = ref(null)
const fullTimestampData = ref(null)
const timeRange = ref([0, 0]) // [minTime, maxTime]
const selectedTimeWindow = ref([0, 0]) // [startTime, endTime]

// 计算当前显示的图表数据
const currentSnapshot = computed(() => {
  return snapshots.value[currentIndex.value]
})

// 当 currentSnapshot 变化时，更新 graphData
const computedGraphData = computed(() => {
  if (currentSnapshot.value) {
    return {
      nodes: currentSnapshot.value.nodes,
      links: currentSnapshot.value.links
    }
  }
  return null
})

// 时间戳模式的过滤逻辑
const filteredTimestampData = computed(() => {
  if (!fullTimestampData.value) return null
  
  const { nodes, links } = fullTimestampData.value
  const [startTime, endTime] = selectedTimeWindow.value
  
  // 过滤边，只保留时间戳在范围内的
  const filteredLinks = links.filter(link => 
    link.timestamp >= startTime && link.timestamp <= endTime
  )
  
  // 收集过滤后边中出现的节点 ID
  const nodeIdsInLinks = new Set()
  filteredLinks.forEach(link => {
    nodeIdsInLinks.add(link.source)
    nodeIdsInLinks.add(link.target)
  })
  
  // 过滤节点，只保留在边中出现过的
  const filteredNodes = nodes.filter(node => nodeIdsInLinks.has(node.id))
  
  return {
    nodes: filteredNodes,
    links: filteredLinks
  }
})

// 监听计算属性的变化，更新 graphData
watch(
  [computedGraphData, filteredTimestampData],
  () => {
    if (currentMode.value === 'snapshot' && computedGraphData.value) {
      graphData.value = computedGraphData.value
    } else if (currentMode.value === 'timestamp' && filteredTimestampData.value) {
      graphData.value = filteredTimestampData.value
    }
  },
  { deep: true }
)

// 当 currentIndex 变化时，更新 graphData
function updateGraphData() {
  if (currentSnapshot.value) {
    graphData.value = {
      nodes: currentSnapshot.value.nodes,
      links: currentSnapshot.value.links
    }
  }
}

// 监听 currentIndex 变化
watch(
  () => currentIndex.value,
  () => {
    updateGraphData()
  }
)

// 更新时间窗口，确保起始时间不大于结束时间
function updateTimeWindow() {
  let [startTime, endTime] = selectedTimeWindow.value
  if (startTime > endTime) {
    // 调整为相等
    selectedTimeWindow.value = [endTime, endTime]
  }
}

async function loadTimestampGraph() {
  try {
    const data = await fetchTimestampGraph()
    fullTimestampData.value = data
    
    // 计算时间范围
    if (data.links.length > 0) {
      const timestamps = data.links.map(link => link.timestamp)
      const minTime = Math.min(...timestamps)
      const maxTime = Math.max(...timestamps)
      timeRange.value = [minTime, maxTime]
      selectedTimeWindow.value = [minTime, maxTime] // 初始化为完整时间范围
    }
    
    currentMode.value = 'timestamp'
    snapshots.value = [] // 清空快照数据
  } catch (error) {
    console.error('加载时间戳图失败:', error)
  }
}

async function loadSnapshotGraphs() {
  try {
    const snapshotData = await fetchSnapshotGraphs()
    snapshots.value = snapshotData
    currentIndex.value = 0 // 重置到第一帧
    currentMode.value = 'snapshot'
    fullTimestampData.value = null // 清空时间戳数据
  } catch (error) {
    console.error('加载快照图失败:', error)
  }
}

function togglePlayPause() {
  if (isPlaying.value) {
    // 暂停
    clearInterval(playInterval)
    playInterval = null
  } else {
    // 播放
    // 如果当前在最后一帧，重置到第一帧
    if (currentIndex.value >= snapshots.value.length - 1) {
      currentIndex.value = 0
      updateGraphData()
    }
    
    // 根据播放速度计算间隔
    const interval = 1500 / parseFloat(playbackSpeed.value)
    
    playInterval = setInterval(() => {
      if (currentIndex.value < snapshots.value.length - 1) {
        currentIndex.value++
        updateGraphData()
      } else {
        // 播放到最后一帧，自动停止
        clearInterval(playInterval)
        playInterval = null
        isPlaying.value = false
      }
    }, interval)
  }
  isPlaying.value = !isPlaying.value
}

// 处理滑块输入，自动暂停播放
function handleSliderInput() {
  if (isPlaying.value) {
    togglePlayPause()
  }
}

// 触发文件上传
function triggerFileUpload() {
  fileInput.value.click()
}

// 处理文件上传
async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  
  // 前端文件格式校验
  const allowedExtensions = ['csv', 'json']
  const fileExtension = file.name.split('.').pop().toLowerCase()
  if (!allowedExtensions.includes(fileExtension)) {
    showToast('请上传 CSV 或 JSON 格式的文件')
    // 清空文件输入
    event.target.value = ''
    return
  }
  
  isLoading.value = true
  
  try {
    const response = await uploadGraphFile(file)
    const { data, detected_mode } = response
    
    if (detected_mode === 'timestamp') {
      // 处理时间戳模式数据
      fullTimestampData.value = data
      
      // 计算时间范围
      if (data.links.length > 0) {
        const timestamps = data.links.map(link => link.timestamp)
        const minTime = Math.min(...timestamps)
        const maxTime = Math.max(...timestamps)
        timeRange.value = [minTime, maxTime]
        selectedTimeWindow.value = [minTime, maxTime] // 初始化为完整时间范围
      }
      
      currentMode.value = 'timestamp'
      snapshots.value = [] // 清空快照数据
    } else {
      // 处理快照模式数据
      snapshots.value = data
      currentIndex.value = 0 // 重置到第一帧
      currentMode.value = 'snapshot'
      fullTimestampData.value = null // 清空时间戳数据
    }
  } catch (error) {
    console.error('文件上传失败:', error)
    showToast(error.message || '数据格式异常或网络请求失败')
  } finally {
    isLoading.value = false
    // 清空文件输入以便重新上传
    event.target.value = ''
  }
}

// Toast 通知函数
function showToast(message) {
  toastMessage.value = message
  toastVisible.value = true
  
  // 清除之前的定时器
  if (toastTimeout) {
    clearTimeout(toastTimeout)
  }
  
  // 3秒后自动隐藏
  toastTimeout = setTimeout(() => {
    hideToast()
  }, 3000)
}

function hideToast() {
  toastVisible.value = false
  setTimeout(() => {
    toastMessage.value = ''
  }, 300)
}

// 组件卸载时清除定时器
onUnmounted(() => {
  if (playInterval) {
    clearInterval(playInterval)
  }
  if (toastTimeout) {
    clearTimeout(toastTimeout)
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #F5F5F7;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

.control-bar {
  background-color: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  color: #1D1D1F;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  height: 80px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.5);
}

.control-bar h1 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1D1D1F;
  letter-spacing: -0.02em;
}

.buttons button {
  margin-left: 1rem;
}

.buttons button {
  margin-left: 1rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background-color: #4CAF50;
  color: white;
  cursor: pointer;
  font-size: 1rem;
}

.buttons button:hover {
  background-color: #45a049;
}

.cyber-btn {
  background: #007AFF;
  border: none;
  border-radius: 24px;
  color: #FFFFFF;
  padding: 0.75rem 2rem;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

.cyber-btn:hover {
  background: #0051D5;
  box-shadow: 0 4px 20px rgba(0, 122, 255, 0.25);
}

.cyber-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.cyber-btn:hover::before {
  left: 100%;
}

.graph-container {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative;
  overflow: hidden;
  background-color: #F5F5F7;
}

.loading {
  font-size: 1.2rem;
  color: #86868B;
}

.timeline {
  background-color: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  color: #1D1D1F;
  padding: 1rem 2rem;
  height: 80px;
  display: flex;
  align-items: center;
  box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.08);
  border-top: 1px solid rgba(255, 255, 255, 0.5);
}

.timeline-controls {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.speed-label {
  color: #86868B;
  font-weight: 500;
  font-size: 0.9rem;
}

.speed-select {
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 12px;
  color: #1D1D1F;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
}

.speed-select:hover {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.speed-select option {
  background: #FFFFFF;
  color: #1D1D1F;
}

.play-pause-btn {
  min-width: 120px;
}

.timeline-slider {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #D2D2D7;
  outline: none;
  border-radius: 3px;
  min-width: 200px;
}

.timeline-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  background: #007AFF;
  cursor: pointer;
  border-radius: 50%;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

.timeline-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  background: #007AFF;
  cursor: pointer;
  border-radius: 50%;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 2rem;
  background: #F5F5F7;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1.5rem;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.empty-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1D1D1F;
  margin-bottom: 0.5rem;
  letter-spacing: -0.02em;
}

.empty-description {
  font-size: 1rem;
  color: #86868B;
  max-width: 400px;
}

/* Loading Mask */
.loading-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(245, 245, 247, 0.85);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: auto;
}

.loading-content {
  text-align: center;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 3px solid rgba(0, 122, 255, 0.15);
  border-top-color: #007AFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: #1D1D1F;
  font-size: 1.1rem;
  font-weight: 500;
  letter-spacing: -0.01em;
}

/* Toast Notification */
.toast-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%) translateY(-100px);
  z-index: 10000;
  transition: transform 0.3s ease;
  pointer-events: none;
}

.toast-container.show {
  transform: translateX(-50%) translateY(0);
  pointer-events: auto;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 59, 48, 0.2);
  border-radius: 16px;
  padding: 16px 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  min-width: 350px;
}

.toast-icon {
  font-size: 1.5rem;
}

.toast-text {
  flex: 1;
  color: #1D1D1F;
  font-size: 1rem;
  font-weight: 500;
}

.toast-close {
  background: none;
  border: none;
  color: #86868B;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.toast-close:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #1D1D1F;
}

.current-time {
  min-width: 150px;
  font-size: 1rem;
  font-weight: 500;
  color: #1D1D1F;
}

.time-window-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 250px;
}

.time-label {
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
  color: #86868B;
  font-weight: 500;
}

</style>
