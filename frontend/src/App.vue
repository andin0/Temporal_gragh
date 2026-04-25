<template>
  <div class="app">
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
      <GraphView v-if="graphData" :graphData="graphData" :mode="currentMode" />
      <div v-else class="loading">点击上方按钮加载图表</div>
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
    alert('文件上传失败: ' + error.message)
  }
}

// 组件卸载时清除定时器
onUnmounted(() => {
  if (playInterval) {
    clearInterval(playInterval)
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
  background-color: #f5f5f5;
}

.control-bar {
  background-color: #333;
  color: white;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  height: 80px;
}

.control-bar h1 {
  font-size: 1.5rem;
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
  background: rgba(0, 30, 60, 0.8);
  border: 1px solid #00f2fe;
  border-radius: 4px;
  color: #00f2fe;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
}

.cyber-btn:hover {
  background: rgba(0, 242, 254, 0.1);
  box-shadow: 0 0 20px rgba(0, 242, 254, 0.6);
  border-color: #00f2fe;
}

.cyber-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(0, 242, 254, 0.2), transparent);
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
}

.loading {
  font-size: 1.2rem;
  color: #666;
}

.timeline {
  background-color: #333;
  color: white;
  padding: 1rem;
  height: 80px;
  display: flex;
  align-items: center;
  box-shadow: 0 -2px 4px rgba(0, 0, 0, 0.1);
}

.timeline-controls {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.speed-label {
  color: #00f2fe;
  font-weight: bold;
  font-size: 0.9rem;
  text-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
}

.speed-select {
  background: rgba(0, 30, 60, 0.8);
  border: 1px solid #00f2fe;
  border-radius: 4px;
  color: #00f2fe;
  padding: 0.3rem 0.6rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.speed-select:hover {
  background: rgba(0, 242, 254, 0.1);
  box-shadow: 0 0 10px rgba(0, 242, 254, 0.5);
}

.speed-select option {
  background: #0f172a;
  color: #00f2fe;
}

.play-pause-btn {
  min-width: 100px;
}

.timeline-slider {
  flex: 1;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: #555;
  outline: none;
  border-radius: 4px;
  min-width: 200px;
}

.timeline-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: #4CAF50;
  cursor: pointer;
  border-radius: 50%;
}

.timeline-slider::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: #4CAF50;
  cursor: pointer;
  border-radius: 50%;
  border: none;
}

.current-time {
  min-width: 150px;
  font-size: 1rem;
  font-weight: bold;
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
  color: #ddd;
}

</style>
