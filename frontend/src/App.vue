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
        <!-- <button v-if="pathSource || pathTarget" class="cyber-btn danger" @click="clearGlobalPath">清除路径</button> -->
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
      <div v-if="!graphData && !isLoading && !snapshots.length" class="empty-state">
        <div class="empty-icon">📊</div>
        <div class="empty-title">暂无数据</div>
        <div class="empty-description">请点击上方按钮上传 CSV/JSON 文件进行图分析</div>
      </div>
      
      <!-- Snapshot Mode: Small Multiples Grid -->
      <div v-else-if="currentMode === 'snapshot' && snapshots.length > 0" class="snapshots-grid">
        <SingleGraph 
          v-for="(snapshot, index) in snapshots" 
          :key="index"
          :data="{ nodes: snapshot.nodes, links: snapshot.links }"
          :title="`T${index + 1}: ${snapshot.timestamp || '快照' + (index + 1)}`"
          :path-source="pathSource"
          :path-target="pathTarget"
          @update:path-source="updatePathSource"
          @update:path-target="updatePathTarget"
          @clear-path="clearGlobalPath"
          @node-select="handleNodeSelect"
        />
      </div>
      
      <!-- Timestamp Mode: Single Graph View -->
      <GraphView v-else-if="currentMode === 'timestamp' && graphData" :graphData="graphData" :mode="currentMode" />
    </main>
    
    <!-- Timestamp Mode Time Window Controls -->
    <footer class="timeline" v-if="currentMode === 'timestamp' && fullTimestampData">
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
    
    <!-- Path Info Bar for Snapshot Mode -->
    <footer v-if="currentMode === 'snapshot' && (pathSource || pathTarget)" class="path-info-bar">
      <div class="path-info-content">
        <div v-if="pathSource" class="path-badge source">📍 起点: <strong>{{ pathSource.id }}</strong></div>
        <div class="path-arrow" v-if="pathTarget">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>
        </div>
        <div v-if="pathTarget" class="path-badge target">🎯 终点: <strong>{{ pathTarget.id }}</strong></div>
        <button class="clear-btn" @click="clearGlobalPath">✕ 清除</button>
      </div>
    </footer>
    
    <!-- Node Detail Drawer -->
    <div 
      v-if="selectedNode" 
      class="node-drawer-overlay" 
      @click="closeDrawer"
    ></div>
    <div 
      v-if="selectedNode" 
      class="node-drawer"
      :class="{ 'open': isDrawerOpen }"
    >
      <div class="drawer-header">
        <h2 class="node-id">{{ selectedNode.id }}</h2>
        <button class="close-btn" @click="closeDrawer">✕</button>
      </div>
      <div class="drawer-content">
        <div class="profile-card">
          <h3 class="card-title">算法研判</h3>
          <div class="profile-item">
            <span class="item-label">核心度得分 (PageRank):</span>
            <span class="item-value">{{ (selectedNode.pagerank || 0).toFixed(4) }}</span>
          </div>
          <div class="profile-item">
            <span class="item-label">所属团伙:</span>
            <div class="group-info">
              <span class="group-color" :style="{ backgroundColor: getColorForGroup(selectedNode.group || 0) }"></span>
              <span class="group-name">Group {{ selectedNode.group || 0 }}</span>
            </div>
          </div>
        </div>
        
        <div class="profile-card">
          <h3 class="card-title">网络指标</h3>
          <div class="profile-item">
            <span class="item-label">度数 (Degree):</span>
            <span class="item-value">{{ selectedNode.degree || 0 }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import GraphView from './components/GraphView.vue'
import SingleGraph from './components/SingleGraph.vue'
import { fetchTimestampGraph, fetchSnapshotGraphs, uploadGraphFile } from './api.js'

const graphData = ref(null)
const snapshots = ref([])
const isLoading = ref(false)
const toastMessage = ref('')
const toastVisible = ref(false)
let toastTimeout = null

const fileInput = ref(null)
const currentMode = ref(null)
const fullTimestampData = ref(null)
const timeRange = ref([0, 0])
const selectedTimeWindow = ref([0, 0])

const selectedNode = ref(null)
const isDrawerOpen = ref(false)

const pathSource = ref(null)
const pathTarget = ref(null)

const filteredTimestampData = computed(() => {
  if (!fullTimestampData.value) return null
  
  const { nodes, links } = fullTimestampData.value
  const [startTime, endTime] = selectedTimeWindow.value
  
  const filteredLinks = links.filter(link => 
    link.timestamp >= startTime && link.timestamp <= endTime
  )
  
  const nodeIdsInLinks = new Set()
  filteredLinks.forEach(link => {
    nodeIdsInLinks.add(link.source)
    nodeIdsInLinks.add(link.target)
  })
  
  const filteredNodes = nodes.filter(node => nodeIdsInLinks.has(node.id))
  
  return {
    nodes: filteredNodes,
    links: filteredLinks
  }
})

watch(
  filteredTimestampData,
  (newData) => {
    if (currentMode.value === 'timestamp' && newData) {
      graphData.value = newData
    }
  },
  { deep: true }
)

function updateTimeWindow() {
  let [startTime, endTime] = selectedTimeWindow.value
  if (startTime > endTime) {
    selectedTimeWindow.value = [endTime, endTime]
  }
}

async function loadTimestampGraph() {
  try {
    const data = await fetchTimestampGraph()
    fullTimestampData.value = data
    
    if (data.links.length > 0) {
      const timestamps = data.links.map(link => link.timestamp)
      const minTime = Math.min(...timestamps)
      const maxTime = Math.max(...timestamps)
      timeRange.value = [minTime, maxTime]
      selectedTimeWindow.value = [minTime, maxTime]
    }
    
    currentMode.value = 'timestamp'
    snapshots.value = []
    clearGlobalPath()
  } catch (error) {
    console.error('加载时间戳图失败:', error)
  }
}

async function loadSnapshotGraphs() {
  try {
    const snapshotData = await fetchSnapshotGraphs()
    snapshots.value = snapshotData
    currentMode.value = 'snapshot'
    fullTimestampData.value = null
    clearGlobalPath()
  } catch (error) {
    console.error('加载快照图失败:', error)
  }
}

function updatePathSource(node) {
  pathSource.value = node
  pathTarget.value = null
}

function updatePathTarget(node) {
  pathTarget.value = node
}

function clearGlobalPath() {
  pathSource.value = null
  pathTarget.value = null
}

function triggerFileUpload() {
  fileInput.value.click()
}

async function handleFileUpload(event) {
  const file = event.target.files[0]
  if (!file) return
  
  const allowedExtensions = ['csv', 'json']
  const fileExtension = file.name.split('.').pop().toLowerCase()
  if (!allowedExtensions.includes(fileExtension)) {
    showToast('请上传 CSV 或 JSON 格式的文件')
    event.target.value = ''
    return
  }
  
  isLoading.value = true
  
  try {
    const response = await uploadGraphFile(file)
    const { data, detected_mode } = response
    
    if (detected_mode === 'timestamp') {
      fullTimestampData.value = data
      
      if (data.links.length > 0) {
        const timestamps = data.links.map(link => link.timestamp)
        const minTime = Math.min(...timestamps)
        const maxTime = Math.max(...timestamps)
        timeRange.value = [minTime, maxTime]
        selectedTimeWindow.value = [minTime, maxTime]
      }
      
      currentMode.value = 'timestamp'
      snapshots.value = []
    } else {
      snapshots.value = data
      currentMode.value = 'snapshot'
      fullTimestampData.value = null
    }
    
    clearGlobalPath()
  } catch (error) {
    console.error('文件上传失败:', error)
    showToast(error.message || '数据格式异常或网络请求失败')
  } finally {
    isLoading.value = false
    event.target.value = ''
  }
}

function showToast(message) {
  toastMessage.value = message
  toastVisible.value = true
  
  if (toastTimeout) {
    clearTimeout(toastTimeout)
  }
  
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

function handleNodeSelect(node) {
  selectedNode.value = node
  setTimeout(() => {
    isDrawerOpen.value = true
  }, 10)
}

function closeDrawer() {
  isDrawerOpen.value = false
  setTimeout(() => {
    selectedNode.value = null
  }, 300)
}

function getColorForGroup(group) {
  const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F']
  return colors[group % colors.length]
}

onUnmounted(() => {
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
  margin-right: 1rem;
}

.buttons button:last-child {
  margin-right: 0;
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

.cyber-btn.danger {
  background: rgba(255, 59, 48, 0.1);
  color: #FF3B30;
  border: 1px solid rgba(255, 59, 48, 0.2);
}

.cyber-btn.danger:hover {
  background: rgba(255, 59, 48, 0.15);
  box-shadow: none;
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
  position: relative;
  overflow: hidden;
  background-color: #F5F5F7;
}

.snapshots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 20px;
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.snapshots-grid > * {
  min-height: 350px;
}

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

.current-time {
  min-width: 150px;
  font-size: 1rem;
  font-weight: 500;
  color: #1D1D1F;
}

.path-info-bar {
  background-color: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  padding: 12px 2rem;
  display: flex;
  align-items: center;
  box-shadow: 0 -8px 32px rgba(0, 0, 0, 0.08);
  border-top: 1px solid rgba(255, 255, 255, 0.5);
}

.path-info-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.path-badge {
  padding: 6px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
}

.path-badge strong { margin-left: 4px; font-weight: 600; }
.path-badge.source { background-color: rgba(52, 199, 89, 0.1); color: #34C759; border: 1px solid rgba(52, 199, 89, 0.2); }
.path-badge.target { background-color: rgba(0, 122, 255, 0.1); color: #007AFF; border: 1px solid rgba(0, 122, 255, 0.2); }
.path-arrow { color: #86868B; display: flex; align-items: center; }

.clear-btn {
  background: rgba(255, 59, 48, 0.1);
  color: #FF3B30;
  border: 1px solid rgba(255, 59, 48, 0.2);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.clear-btn:hover {
  background: rgba(255, 59, 48, 0.15);
}

.node-drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  z-index: 9998;
  opacity: 0;
  animation: fadeIn 0.3s ease forwards;
}

@keyframes fadeIn {
  to { opacity: 1; }
}

.node-drawer {
  position: fixed;
  top: 0;
  right: -400px;
  width: 350px;
  height: 100vh;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-left: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: -8px 0 32px rgba(0, 0, 0, 0.08);
  z-index: 9999;
  transition: right 0.3s ease;
  overflow-y: auto;
  color: #1D1D1F;
}

.node-drawer.open {
  right: 0;
}

.drawer-header {
  padding: 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.5);
  position: sticky;
  top: 0;
  z-index: 10;
}

.node-id {
  font-size: 20px;
  font-weight: 600;
  color: #1D1D1F;
  letter-spacing: -0.02em;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  color: #86868B;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #1D1D1F;
}

.drawer-content {
  padding: 20px;
}

.profile-card {
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #1D1D1F;
  letter-spacing: -0.02em;
}

.profile-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.profile-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.item-label {
  font-size: 14px;
  color: #86868B;
}

.item-value {
  font-size: 14px;
  font-weight: 500;
  color: #1D1D1F;
}

.group-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.group-name {
  font-size: 14px;
  font-weight: 500;
  color: #1D1D1F;
}

.node-drawer::-webkit-scrollbar {
  width: 6px;
}

.node-drawer::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
}

.node-drawer::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
}

.node-drawer::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

@keyframes dash {
  to { stroke-dashoffset: -20; }
}
</style>