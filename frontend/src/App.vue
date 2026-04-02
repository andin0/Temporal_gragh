<template>
  <div class="app">
    <header class="control-bar">
      <h1>时序图可视化</h1>
      <div class="buttons">
        <div class="upload-btn-container">
          <button @click="triggerFileUpload('timestamp')">上传时间戳数据 (CSV/JSON)</button>
          <input 
            type="file" 
            ref="timestampFileInput" 
            style="display: none" 
            accept=".csv,.json"
            @change="handleFileUpload($event, 'timestamp')"
          />
        </div>
        <div class="upload-btn-container">
          <button @click="triggerFileUpload('snapshot')">上传快照数据 (CSV/JSON)</button>
          <input 
            type="file" 
            ref="snapshotFileInput" 
            style="display: none" 
            accept=".csv,.json"
            @change="handleFileUpload($event, 'snapshot')"
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
        <button @click="togglePlayPause" class="play-pause-btn">
          {{ isPlaying ? '暂停' : '播放' }}
        </button>
        <input 
          type="range" 
          class="timeline-slider" 
          :min="0" 
          :max="snapshots.length - 1" 
          v-model.number="currentIndex"
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
let playInterval = null

// 文件输入框引用
const timestampFileInput = ref(null)
const snapshotFileInput = ref(null)

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
    }, 1500) // 1.5 秒切换一次
  }
  isPlaying.value = !isPlaying.value
}

// 触发文件上传
function triggerFileUpload(mode) {
  if (mode === 'timestamp') {
    timestampFileInput.value.click()
  } else {
    snapshotFileInput.value.click()
  }
}

// 处理文件上传
async function handleFileUpload(event, mode) {
  const file = event.target.files[0]
  if (!file) return
  
  try {
    const result = await uploadGraphFile(file, mode)
    
    if (mode === 'timestamp') {
      // 处理时间戳模式数据
      fullTimestampData.value = result
      
      // 计算时间范围
      if (result.links.length > 0) {
        const timestamps = result.links.map(link => link.timestamp)
        const minTime = Math.min(...timestamps)
        const maxTime = Math.max(...timestamps)
        timeRange.value = [minTime, maxTime]
        selectedTimeWindow.value = [minTime, maxTime] // 初始化为完整时间范围
      }
      
      currentMode.value = 'timestamp'
      snapshots.value = [] // 清空快照数据
    } else {
      // 处理快照模式数据
      snapshots.value = result
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

.play-pause-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background-color: #4CAF50;
  color: white;
  cursor: pointer;
  font-size: 1rem;
  min-width: 80px;
}

.play-pause-btn:hover {
  background-color: #45a049;
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
